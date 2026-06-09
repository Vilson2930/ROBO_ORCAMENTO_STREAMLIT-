# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — identifica somente parcelamentos reais
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


TERMOS_BLOQUEADOS = [
    "PAGAMENTO",
    "PAGAMENTO ONLINE",
    "PAGAMENTO ON LINE",
    "PAGAMENTO MINIMO",
    "PAGAMENTO TOTAL",
    "PIX",
    "BOLETO",
    "ESTORNO",
    "CREDITO",
    "CREDITO DE PAGAMENTO",
    "JUROS",
    "IOF",
    "ENCARGOS",
    "ROTATIVO",
    "SALDO",
    "TOTAL DA FATURA",
    "DESPESAS DA FATURA",
    "FATURA",
]


PADROES_PARCELA = [
    r"\bPARCELA\s*(\d{1,2})\s*DE\s*(\d{1,2})\b",
    r"\bPARC(?:ELA)?\.?\s*(\d{1,2})\s*/\s*(\d{1,2})\b",
    r"\bPARC(?:ELA)?\.?\s*(\d{1,2})\s*DE\s*(\d{1,2})\b",
    r"\bCOMPRA\s*PARCELADA\s*(\d{1,2})\s*/\s*(\d{1,2})\b",
    r"\bPARCELADO\s*(\d{1,2})\s*/\s*(\d{1,2})\b",
    r"\b(\d{1,2})\s*/\s*(\d{1,2})\b",
]


PADRAO_X = re.compile(r"\b(\d{1,2})\s*X\b", re.IGNORECASE)


def contem_bloqueado(texto):
    texto = normalizar_texto(texto)

    for termo in TERMOS_BLOQUEADOS:
        if termo in texto:
            return True

    return False


def extrair_parcela(texto):
    texto = normalizar_texto(texto)

    if not texto:
        return None, None

    if contem_bloqueado(texto):
        return None, None

    for padrao in PADROES_PARCELA:
        m = re.search(padrao, texto)

        if not m:
            continue

        atual = int(m.group(1))
        total = int(m.group(2))

        if total <= 1:
            continue

        if total > 60:
            continue

        if atual < 1 or atual > total:
            continue

        return atual, total

    m = PADRAO_X.search(texto)

    if m:
        total = int(m.group(1))

        if 2 <= total <= 60:
            return 1, total

    return None, None


def limpar_compra(texto):
    texto = normalizar_texto(texto)

    limpezas = [
        r"\bPARCELA\s*\d{1,2}\s*DE\s*\d{1,2}\b",
        r"\bPARC(?:ELA)?\.?\s*\d{1,2}\s*/\s*\d{1,2}\b",
        r"\bPARC(?:ELA)?\.?\s*\d{1,2}\s*DE\s*\d{1,2}\b",
        r"\bCOMPRA\s*PARCELADA\s*\d{1,2}\s*/\s*\d{1,2}\b",
        r"\bPARCELADO\s*\d{1,2}\s*/\s*\d{1,2}\b",
        r"\b\d{1,2}\s*/\s*\d{1,2}\b",
        r"\b\d{1,2}\s*X\b",
        r"COMPRA PARCELADA",
        r"PARCELADO",
        r"PARCELAMENTO",
    ]

    for padrao in limpezas:
        texto = re.sub(padrao, "", texto)

    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" -")


def encontrar_coluna_descricao(df):
    for col in [
        "descricao_original",
        "descricao",
        "merchant",
        "estabelecimento",
        "compra",
        "texto",
        "lancamento",
    ]:
        if col in df.columns:
            return col

    for col in df.columns:
        if df[col].dtype == "object":
            return col

    return None


def encontrar_coluna_valor(df):
    for col in [
        "valor",
        "valor_total",
        "total",
        "amount",
        "gasto",
    ]:
        if col in df.columns:
            return col

    numericas = df.select_dtypes(include="number").columns.tolist()
    return numericas[0] if numericas else None


def processar_parcelamentos(df):
    if df is None or df.empty:
        return pd.DataFrame()

    temp = df.copy()

    coluna_desc = encontrar_coluna_descricao(temp)
    coluna_valor = encontrar_coluna_valor(temp)

    if coluna_desc is None or coluna_valor is None:
        return pd.DataFrame()

    temp[coluna_valor] = pd.to_numeric(temp[coluna_valor], errors="coerce").fillna(0)

    resultado = []

    for _, linha in temp.iterrows():
        descricao = str(linha.get(coluna_desc, ""))
        valor_parcela = float(linha.get(coluna_valor, 0))

        if valor_parcela <= 0:
            continue

        parcela_atual, total_parcelas = extrair_parcela(descricao)

        if parcela_atual is None or total_parcelas is None:
            continue

        compra = limpar_compra(descricao)

        if not compra:
            continue

        if contem_bloqueado(compra):
            continue

        parcelas_abertas = max(total_parcelas - parcela_atual, 0)
        valor_restante = parcelas_abertas * valor_parcela

        resultado.append({
            "compra": compra,
            "categoria": linha.get("categoria", "Outros"),
            "ultima_parcela": parcela_atual,
            "total_parcelas": total_parcelas,
            "parcelas_pagas": parcela_atual,
            "parcelas_abertas": parcelas_abertas,
            "valor_parcela": valor_parcela,
            "valor_total_compra": total_parcelas * valor_parcela,
            "valor_pago": parcela_atual * valor_parcela,
            "valor_restante": valor_restante,
            "status": "QUITADO" if parcelas_abertas == 0 else "ABERTO",
            "descricao_detectada": descricao,
        })

    if not resultado:
        return pd.DataFrame()

    df_resultado = pd.DataFrame(resultado)

    df_resultado = df_resultado.drop_duplicates(
        subset=[
            "compra",
            "ultima_parcela",
            "total_parcelas",
            "valor_parcela",
        ]
    )

    df_resultado = df_resultado.sort_values(
        "valor_restante",
        ascending=False
    ).reset_index(drop=True)

    return df_resultado


def resumo_parcelamentos(df_parcelamentos):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return {
            "parcelamentos": 0,
            "abertos": 0,
            "quitados": 0,
            "valor_restante": 0.0,
            "valor_total_compras": 0.0,
            "maior_compromisso": 0.0,
        }

    abertos = df_parcelamentos[df_parcelamentos["status"] == "ABERTO"]
    quitados = df_parcelamentos[df_parcelamentos["status"] == "QUITADO"]

    return {
        "parcelamentos": int(len(df_parcelamentos)),
        "abertos": int(len(abertos)),
        "quitados": int(len(quitados)),
        "valor_restante": float(abertos["valor_restante"].sum()),
        "valor_total_compras": float(df_parcelamentos["valor_total_compra"].sum()),
        "maior_compromisso": float(abertos["valor_restante"].max()) if not abertos.empty else 0.0,
    }
