# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão blindada — aceita df_base e não quebra o app
# Lê somente COMPRAS PARCELADAS reais
# Bloqueia parcelamento de fatura, CET, IOF, rotativo, simulações e anuidade
# ============================================================

import re
import pandas as pd
import unicodedata


def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper().replace("ª", "A").replace("º", "O")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def converter_valor(valor):
    try:
        return float(str(valor).replace(".", "").replace(",", "."))
    except Exception:
        return 0.0


def linha_administrativa(linha):
    t = normalizar_texto(linha)

    bloqueios = [
        "VALOR TOTAL", "TOTAL DA FATURA", "TOTAL A PAGAR", "TOTAL FINAL",
        "TOTAL COMPRAS", "PAGAMENTO", "OBRIGADO PELO PAGAMENTO",
        "CREDITO", "AJUSTE", "ESTORNO", "LIMITE", "VENCIMENTO",
        "ROTATIVO", "IOF", "CET", "JUROS", "MULTA", "MORA",
        "PARCELAMENTO DE FATURA", "PARCELE A SUA FATURA",
        "OPCOES PARA PAGAMENTO", "OPÇÕES PARA PAGAMENTO",
        "QTD", "1A PARCELA", "DEMAIS PARCELAS", "JUROS EFETIVOS",
        "TOTAL DAS PARCELAS", "TOTAL DEVIDO", "SIMULAR", "ESCOLHA",
        "VALOR ORIGINAL", "COTACAO", "COTAÇÃO", "DATA DESCRICAO",
        "CIDADE/PAIS", "CREDITO/DEBITO", "LEGENDA", "APP CARTOES",
        "CENTRAL DE ATENDIMENTO", "INFORMACOES COMPLEMENTARES",
        "OPERACAO CONTRATADA", "OPERAÇÃO CONTRATADA",
        "ANUIDADE", "ANUIDADE DIFERENCIADA"
    ]

    if any(b in t for b in bloqueios):
        return True

    if "%" in t:
        return True

    if re.search(r"\b\d{1,2}X\s+R\$", t):
        return True

    return False


def extrair_parcela_texto(linha):
    t = normalizar_texto(linha)

    padroes = [
        r"(?P<atual>\d{1,2})\s+DE\s+(?P<total>\d{1,2})",
        r"PARCELA\s*(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})",
        r"(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})",
    ]

    for p in padroes:
        m = re.search(p, t)
        if m:
            atual = int(m.group("atual"))
            total = int(m.group("total"))
            if 1 <= atual <= total <= 60:
                return atual, total

    return 0, 0


def extrair_valor_linha(linha):
    valores = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})D?", str(linha))
    return converter_valor(valores[-1]) if valores else 0.0


def limpar_compra(linha):
    t = normalizar_texto(linha)
    t = re.sub(r"^\d{2}/\d{2}\s+", "", t)
    t = re.sub(r"\b\d{1,2}\s+DE\s+\d{1,2}\b", "", t)
    t = re.sub(r"\bPARCELA\s*\d{1,2}/\d{1,2}\b", "", t)
    t = re.sub(r"\b\d{1,2}/\d{1,2}\b", "", t)
    t = re.sub(r"\d{1,3}(?:\.\d{3})*,\d{2}D?$", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip(" -")


def chave_compra(texto):
    t = normalizar_texto(texto)
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def compra_valida(compra):
    t = normalizar_texto(compra)

    if len(t) < 3 or len(t) > 90:
        return False

    if linha_administrativa(t):
        return False

    if "%" in t or "R$" in t:
        return False

    if not re.search(r"[A-Z]", t):
        return False

    return True


def extrair_parcelamentos_documento(texto, arquivo=""):
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    registros = []
    dentro = False

    for linha in linhas:
        ln = normalizar_texto(linha)

        if "COMPRAS PARCELADAS" in ln:
            dentro = True
            continue

        if any(x in ln for x in [
            "TOTAL COMPRAS PARCELADAS",
            "OUTROS (",
            "TOTAL FINAL",
            "VALOR TOTAL DESTA FATURA",
            "LEGENDA",
            "OPERACAO CONTRATADA",
            "OPERAÇÃO CONTRATADA",
            "APP CARTOES",
            "APP CARTÕES",
        ]):
            dentro = False
            continue

        if not dentro:
            continue

        if linha_administrativa(ln):
            continue

        atual, total = extrair_parcela_texto(ln)
        if total <= 0:
            continue

        valor_parcela = extrair_valor_linha(linha)
        if valor_parcela <= 0:
            continue

        compra = limpar_compra(linha)
        if not compra_valida(compra):
            continue

        parcelas_abertas = max(total - atual, 0)

        registros.append({
            "arquivo_fatura": arquivo,
            "compra": compra,
            "compra_key": chave_compra(compra),
            "ultima_parcela": atual,
            "total_parcelas": total,
            "valor_parcela": valor_parcela,
            "parcelas_abertas": parcelas_abertas,
            "valor_restante": round(parcelas_abertas * valor_parcela, 2),
            "valor_total_compra": round(total * valor_parcela, 2),
            "status": "ABERTO" if parcelas_abertas > 0 else "FINALIZADO",
            "descricao_detectada": linha,
        })

    return registros


def processar_parcelamentos(documentos, df_base=None, *args, **kwargs):
    todos = []

    for doc in documentos:
        todos.extend(
            extrair_parcelamentos_documento(
                texto=doc.get("texto", ""),
                arquivo=doc.get("arquivo", "")
            )
        )

    colunas = [
        "arquivo_fatura", "compra", "compra_key", "ultima_parcela",
        "total_parcelas", "valor_parcela", "parcelas_abertas",
        "valor_restante", "valor_total_compra", "status",
        "descricao_detectada"
    ]

    df = pd.DataFrame(todos, columns=colunas)

    if df.empty:
        return df

    for c in [
        "ultima_parcela", "total_parcelas", "valor_parcela",
        "parcelas_abertas", "valor_restante", "valor_total_compra"
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["compra_key", "valor_parcela", "ultima_parcela", "total_parcelas"])
    df = df[df["valor_parcela"] > 0]

    df = df[df["compra"].apply(compra_valida)]

    df = df.sort_values(["compra_key", "ultima_parcela"], ascending=[True, False])

    df = df.drop_duplicates(
        subset=["compra_key", "total_parcelas", "valor_parcela"],
        keep="first"
    )

    df = df.sort_values(
        ["valor_restante", "valor_parcela"],
        ascending=False
    ).reset_index(drop=True)

    return df


def resumo_parcelamentos(df):
    if df is None or df.empty:
        return {
            "quantidade": 0,
            "valor_futuro": 0.0,
            "impacto_mensal": 0.0,
            "maior_parcela": 0.0,
            "maior_compra": "-",
        }

    abertos = df[df["status"] == "ABERTO"].copy()

    if abertos.empty:
        return {
            "quantidade": 0,
            "valor_futuro": 0.0,
            "impacto_mensal": 0.0,
            "maior_parcela": 0.0,
            "maior_compra": "-",
        }

    maior = abertos.sort_values("valor_parcela", ascending=False).iloc[0]

    return {
        "quantidade": int(len(abertos)),
        "valor_futuro": round(float(abertos["valor_restante"].sum()), 2),
        "impacto_mensal": round(float(abertos["valor_parcela"].sum()), 2),
        "maior_parcela": round(float(maior["valor_parcela"]), 2),
        "maior_compra": str(maior["compra"]),
    }
