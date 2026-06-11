# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Corrigido: lê somente compras parceladas reais
# Bloqueia simulação de parcelamento de fatura, CET, rotativo e ofertas
# ============================================================

import re
import pandas as pd
import unicodedata


def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def converter_valor(valor):
    return float(str(valor).replace(".", "").replace(",", "."))


def limpar_compra(texto):
    texto = str(texto or "")
    texto = re.sub(r"R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}", "", texto)
    texto = re.sub(r"\d{1,2}/\d{1,2}", "", texto)
    texto = re.sub(r"\d{1,2}\s+DE\s+\d{1,2}", "", texto, flags=re.I)
    texto = re.sub(r"\d{2}/\d{2}", "", texto)
    texto = re.sub(r"\d{1,3}(?:\.\d{3})*,\d{2}D?$", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" -")


def chave_compra(texto):
    texto = normalizar_texto(texto)
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def linha_administrativa(linha):
    t = normalizar_texto(linha)

    bloqueios = [
        "VALOR TOTAL", "TOTAL DA FATURA", "TOTAL A PAGAR",
        "PAGAMENTO", "OBRIGADO PELO PAGAMENTO",
        "CREDITO", "CREDITO PARC", "AJUSTE CREDITO",
        "ESTORNO", "LIMITE", "VENCIMENTO",
        "ROTATIVO", "IOF", "CET", "JUROS", "MULTA", "MORA",
        "PARCELAMENTO DE FATURA", "OPCOES PARA PAGAMENTO",
        "OPÇÕES PARA PAGAMENTO", "QTD PARCELAS",
        "1A PARCELA", "1ª PARCELA", "DEMAIS PARCELAS",
        "JUROS EFETIVOS", "TOTAL DAS PARCELAS",
        "TOTAL DEVIDO", "AO CONTRATAR",
        "ESCOLHA UMA DAS OPCOES", "ESCOLHA UMA DAS OPÇÕES",
        "SIMULAR OUTRAS OPCOES", "SIMULAR OUTRAS OPÇÕES",
        "VALOR ORIGINAL", "COTACAO", "COTAÇÃO",
        "DATA DESCRICAO", "DATA DESCRIÇÃO",
        "CIDADE/PAIS", "CIDADE/PAÍS",
        "CREDITO/DEBITO", "CRÉDITO/DÉBITO",
        "LEGEND", "LEGENDA", "APP CARTOES", "APP CARTÕES",
        "CENTRAL DE ATENDIMENTO", "INFORMACOES COMPLEMENTARES",
        "INFORMAÇÕES COMPLEMENTARES",
    ]

    if any(b in t for b in bloqueios):
        return True

    if t.count("%") >= 2:
        return True

    if t.count("R$") >= 3:
        return True

    if re.search(r"\b\d{1,2}X\s+R\$", t):
        return True

    return False


def compra_valida(compra):
    t = normalizar_texto(compra)

    if not t or len(t) < 3:
        return False

    if linha_administrativa(t):
        return False

    if len(t) > 90:
        return False

    if not re.search(r"[A-Z]", t):
        return False

    if t.count("%") > 0:
        return False

    return True


def extrair_parcela_texto(linha):
    t = normalizar_texto(linha)

    padroes = [
        r"(?P<atual>\d{1,2})\s*DE\s*(?P<total>\d{1,2})",
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

    if not valores:
        return 0.0

    return converter_valor(valores[-1])


def extrair_parcelamentos_documento(texto, arquivo=""):
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    registros = []

    dentro_compras_parceladas = False
    bloqueio_oferta_fatura = False

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if "PARCELAMENTO DE FATURA" in linha_norm:
            bloqueio_oferta_fatura = True
            dentro_compras_parceladas = False
            continue

        if "DEMONSTRATIVO" in linha_norm:
            bloqueio_oferta_fatura = False
            continue

        if bloqueio_oferta_fatura:
            continue

        if "COMPRAS PARCELADAS" in linha_norm:
            dentro_compras_parceladas = True
            continue

        if (
            "TOTAL COMPRAS PARCELADAS" in linha_norm
            or "OUTROS (" in linha_norm
            or "TOTAL FINAL" in linha_norm
            or "VALOR TOTAL DESTA FATURA" in linha_norm
            or "LEGENDA" in linha_norm
            or "OPERACAO CONTRATADA" in linha_norm
            or "OPERAÇÃO CONTRATADA" in linha_norm
        ):
            dentro_compras_parceladas = False
            continue

        if not dentro_compras_parceladas:
            continue

        if linha_administrativa(linha_norm):
            continue

        atual, total = extrair_parcela_texto(linha_norm)

        if total <= 0:
            continue

        valor_parcela = extrair_valor_linha(linha)

        if valor_parcela <= 0:
            continue

        compra = limpar_compra(linha_norm)

        compra = re.sub(r"\b\d{1,2}\s+DE\s+\d{1,2}\b", "", compra)
        compra = re.sub(r"\b\d{1,2}/\d{1,2}\b", "", compra)
        compra = re.sub(r"\s+", " ", compra).strip()

        if not compra_valida(compra):
            continue

        parcelas_abertas = max(total - atual, 0)
        valor_restante = parcelas_abertas * valor_parcela

        if parcelas_abertas <= 0:
            status = "FINALIZADO"
        else:
            status = "ABERTO"

        registros.append({
            "arquivo_fatura": arquivo,
            "compra": compra,
            "compra_key": chave_compra(compra),
            "ultima_parcela": atual,
            "total_parcelas": total,
            "valor_parcela": valor_parcela,
            "parcelas_abertas": parcelas_abertas,
            "valor_restante": valor_restante,
            "valor_total_compra": total * valor_parcela,
            "status": status,
            "descricao_detectada": linha,
        })

    return registros


def processar_parcelamentos(documentos):
    todos = []

    for doc in documentos:
        arquivo = doc.get("arquivo", "")
        texto = doc.get("texto", "")

        todos.extend(
            extrair_parcelamentos_documento(
                texto=texto,
                arquivo=arquivo
            )
        )

    colunas = [
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

    df = pd.DataFrame(todos, columns=colunas)

    if df.empty:
        return df

    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce")
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce")
    df["valor_restante"] = pd.to_numeric(df["valor_restante"], errors="coerce")
    df["valor_total_compra"] = pd.to_numeric(df["valor_total_compra"], errors="coerce")

    df = df.dropna(subset=["valor_parcela", "parcelas_abertas", "valor_restante"])
    df = df[df["valor_parcela"] > 0]

    df = df.drop_duplicates(
        subset=["arquivo_fatura", "compra_key", "ultima_parcela", "total_parcelas", "valor_parcela"]
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
        "valor_futuro": float(abertos["valor_restante"].sum()),
        "impacto_mensal": float(abertos["valor_parcela"].sum()),
        "maior_parcela": float(maior["valor_parcela"]),
        "maior_compra": str(maior["compra"]),
    }
