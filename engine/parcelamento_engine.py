# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Motor universal por padrão estrutural
# Lê parcelamentos reais em qualquer fatura textual
# Bloqueia: parcelamento de fatura, CET, IOF, rotativo, juros,
# simulações, pagamentos, totais, anuidade e textos administrativos
# ============================================================

import re
import pandas as pd
import unicodedata


COLUNAS = [
    "arquivo_fatura",
    "compra",
    "compra_key",
    "ultima_parcela",
    "total_parcelas",
    "valor_parcela",
    "parcelas_abertas",
    "valor_restante",
    "valor_total_compra",
    "status",
    "descricao_detectada",
]


def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = texto.replace("ª", "A").replace("º", "O")
    texto = texto.replace("−", "-").replace("–", "-").replace("—", "-")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def converter_valor(valor):
    try:
        valor = str(valor).replace("R$", "").strip()
        valor = valor.replace(".", "").replace(",", ".")
        return float(valor)
    except Exception:
        return 0.0


def linha_administrativa(linha):
    t = normalizar_texto(linha)

    bloqueios = [
        "VALOR TOTAL", "TOTAL DA FATURA", "TOTAL A PAGAR", "TOTAL FINAL",
        "TOTAL COMPRAS", "TOTAL OUTROS", "TOTAL DEVIDO",
        "PAGAMENTO", "OBRIGADO PELO PAGAMENTO", "PAGAMENTO RECEBIDO",
        "CREDITO", "CRÉDITO", "AJUSTE", "ESTORNO",
        "LIMITE", "VENCIMENTO", "VALOR DO DOCUMENTO",
        "ROTATIVO", "ATRASO", "IOF", "CET", "JUROS", "MULTA", "MORA",
        "PARCELAMENTO DE FATURA", "PARCELE A SUA FATURA",
        "OPCOES PARA PAGAMENTO", "OPÇÕES PARA PAGAMENTO",
        "QTD", "1A PARCELA", "1 PARCELA", "DEMAIS PARCELAS",
        "JUROS EFETIVOS", "SIMULAR", "ESCOLHA",
        "VALOR ORIGINAL", "COTACAO", "COTAÇÃO",
        "DATA DESCRICAO", "DATA DESCRIÇÃO", "CIDADE/PAIS", "CIDADE/PAÍS",
        "CREDITO/DEBITO", "CRÉDITO/DÉBITO",
        "LEGENDA", "APP CARTOES", "APP CARTÕES",
        "CENTRAL DE ATENDIMENTO", "INFORMACOES COMPLEMENTARES",
        "INFORMAÇÕES COMPLEMENTARES", "OPERACAO CONTRATADA", "OPERAÇÃO CONTRATADA",
        "ANUIDADE", "TARIFA", "ENCARGOS",
    ]

    if any(b in t for b in bloqueios):
        return True

    if "%" in t:
        return True

    if re.search(r"\b\d{1,2}X\s+R\$", t):
        return True

    if len(re.findall(r"R\$", t)) >= 2:
        return True

    return False


def extrair_parcela_texto(linha):
    t = normalizar_texto(linha)

    padroes = [
        r"\bPARCELA\s*(?P<atual>\d{1,2})\s*(?:DE|/)\s*(?P<total>\d{1,2})\b",
        r"\bPARC\s*(?P<atual>\d{1,2})\s*(?:DE|/)\s*(?P<total>\d{1,2})\b",
        r"\b(?P<atual>\d{1,2})\s+DE\s+(?P<total>\d{1,2})\b",
        r"\b(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    ]

    for p in padroes:
        m = re.search(p, t)
        if m:
            atual = int(m.group("atual"))
            total = int(m.group("total"))

            if 1 <= atual <= total <= 60 and total > 1:
                return atual, total

    return 0, 0


def extrair_valor_linha(linha):
    valores = re.findall(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})\s*D?\b", str(linha))
    if not valores:
        return 0.0
    return converter_valor(valores[-1])


def limpar_compra(linha):
    t = normalizar_texto(linha)

    t = re.sub(r"^\d{1,2}/\d{1,2}\s+", "", t)
    t = re.sub(r"\b\d{1,2}\s+DE\s+\d{1,2}\b", "", t)
    t = re.sub(r"\bPARCELA\s*\d{1,2}\s*(?:DE|/)\s*\d{1,2}\b", "", t)
    t = re.sub(r"\bPARC\s*\d{1,2}\s*(?:DE|/)\s*\d{1,2}\b", "", t)
    t = re.sub(r"\b\d{1,2}/\d{1,2}\b", "", t)
    t = re.sub(r"(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2}\s*D?$", "", t)
    t = re.sub(r"\b\d{1,3},\d{4}\b", "", t)
    t = re.sub(r"\s+", " ", t)

    return t.strip(" -")


def chave_compra(texto):
    t = normalizar_texto(texto)
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\b(SAO PAULO|CURITIBA|GUARAPUAVA|PR|SP|BRASIL)\b", " ", t)
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


def unir_linhas_quebradas(texto):
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    unidas = []

    for linha in linhas:
        ln = normalizar_texto(linha)

        if not unidas:
            unidas.append(linha)
            continue

        anterior = normalizar_texto(unidas[-1])

        valor_na_linha = re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}\s*D?\b", ln)
        parcela_na_anterior = extrair_parcela_texto(anterior) != (0, 0)

        if parcela_na_anterior and valor_na_linha and len(anterior) < 120:
            unidas[-1] = unidas[-1] + " " + linha
        else:
            unidas.append(linha)

    return unidas


def extrair_parcelamentos_documento(texto, arquivo=""):
    linhas = unir_linhas_quebradas(texto)
    registros = []

    for linha in linhas:
        ln = normalizar_texto(linha)

        if linha_administrativa(ln):
            continue

        atual, total = extrair_parcela_texto(ln)
        if total <= 1:
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
            "valor_parcela": round(valor_parcela, 2),
            "parcelas_abertas": int(parcelas_abertas),
            "valor_restante": round(parcelas_abertas * valor_parcela, 2),
            "valor_total_compra": round(total * valor_parcela, 2),
            "status": "ABERTO" if parcelas_abertas > 0 else "FINALIZADO",
            "descricao_detectada": linha,
        })

    return registros


def processar_parcelamentos(documentos, df_base=None, *args, **kwargs):
    todos = []

    for doc in documentos or []:
        todos.extend(
            extrair_parcelamentos_documento(
                texto=doc.get("texto", ""),
                arquivo=doc.get("arquivo", "")
            )
        )

    df = pd.DataFrame(todos, columns=COLUNAS)

    if df.empty:
        return pd.DataFrame(columns=COLUNAS)

    for c in [
        "ultima_parcela", "total_parcelas", "valor_parcela",
        "parcelas_abertas", "valor_restante", "valor_total_compra"
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["compra_key", "valor_parcela", "ultima_parcela", "total_parcelas"])
    df = df[df["valor_parcela"] > 0]

    # Mantém somente a parcela mais recente da mesma compra
    df = df.sort_values(
        ["compra_key", "total_parcelas", "valor_parcela", "ultima_parcela"],
        ascending=[True, True, True, False]
    )

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
