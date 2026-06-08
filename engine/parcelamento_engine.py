# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão profissional — identifica compras parceladas em múltiplos padrões
# ============================================================

import re
import pandas as pd


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_texto(texto):
    texto = str(texto).upper()

    texto = texto.replace("Á", "A")
    texto = texto.replace("À", "A")
    texto = texto.replace("Ã", "A")
    texto = texto.replace("Â", "A")
    texto = texto.replace("É", "E")
    texto = texto.replace("Ê", "E")
    texto = texto.replace("Í", "I")
    texto = texto.replace("Ó", "O")
    texto = texto.replace("Õ", "O")
    texto = texto.replace("Ô", "O")
    texto = texto.replace("Ú", "U")
    texto = texto.replace("Ç", "C")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# ============================================================
# EXTRAIR PARCELA
# ============================================================

def extrair_parcela(texto):
    """
    Reconhece padrões como:

    PARCELA 1 DE 12
    PARCELA 01 DE 12
    PARC 1 DE 12
    PARC 01/12
    1 DE 12
    01/12
    10/12
    3/10
    12X
    10X
    COMPRA PARCELADA 5/10
    """

    texto = normalizar_texto(texto)

    padroes = [

        # PARCELA 1 DE 12 / PARC 1 DE 12
        r"(?:PARCELA|PARC)\s*(\d{1,2})\s*(?:DE|/)\s*(\d{1,2})",

        # 1 DE 12
        r"\b(\d{1,2})\s*DE\s*(\d{1,2})\b",

        # 01/12, 1/12, 10/12
        r"\b(\d{1,2})\s*/\s*(\d{1,2})\b",

        # 12X ou 10X — assume parcela atual 1
        r"\b(\d{1,2})\s*X\b",
    ]

    for padrao in padroes:

        match = re.search(padrao, texto)

        if match:

            if "X" in padrao:
                atual = 1
                total = int(match.group(1))
            else:
                atual = int(match.group(1))
                total = int(match.group(2))

            if total <= 1:
                continue

            if atual < 1:
                continue

            if atual > total:
                continue

            return atual, total

    return None, None


# ============================================================
# LIMPAR NOME DA COMPRA
# ============================================================

def limpar_compra(texto):
    texto = normalizar_texto(texto)

    padroes_limpeza = [
        r"\(PARCELA\s*\d{1,2}\s*DE\s*\d{1,2}\)",
        r"PARCELA\s*\d{1,2}\s*DE\s*\d{1,2}",
        r"PARC\s*\d{1,2}\s*DE\s*\d{1,2}",
        r"PARC\s*\d{1,2}\s*/\s*\d{1,2}",
        r"\b\d{1,2}\s*DE\s*\d{1,2}\b",
        r"\b\d{1,2}\s*/\s*\d{1,2}\b",
        r"\b\d{1,2}\s*X\b",
        r"COMPRA PARCELADA",
        r"PARCELADO",
        r"PARCELAMENTO",
    ]

    for padrao in padroes_limpeza:
        texto = re.sub(padrao, "", texto)

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# ============================================================
# ENCONTRAR COLUNAS
# ============================================================

def encontrar_coluna_descricao(df):
    candidatos = [
        "descricao_original",
        "descrição_original",
        "descricao",
        "descrição",
        "merchant",
        "estabelecimento",
        "compra",
        "texto",
        "lancamento",
        "lançamento",
    ]

    for candidato in candidatos:
        if candidato in df.columns:
            return candidato

    for col in df.columns:
        if df[col].dtype == "object":
            return col

    return None


def encontrar_coluna_valor(df):
    candidatos = [
        "valor",
        "valor_total",
        "total",
        "amount",
        "gasto",
        "preco",
        "preço",
    ]

    for candidato in candidatos:
        if candidato in df.columns:
            return candidato

    numericas = df.select_dtypes(include="number").columns.tolist()

    if numericas:
        return numericas[0]

    return None


# ============================================================
# PROCESSAR PARCELAMENTOS
# ============================================================

def processar_parcelamentos(df):

    if df is None or len(df) == 0:
        return pd.DataFrame()

    temp = df.copy()

    coluna_descricao = encontrar_coluna_descricao(temp)
    coluna_valor = encontrar_coluna_valor(temp)

    if coluna_descricao is None or coluna_valor is None:
        return pd.DataFrame()

    temp[coluna_valor] = pd.to_numeric(
        temp[coluna_valor],
        errors="coerce"
    ).fillna(0)

    temp["descricao_parcelamento"] = temp[coluna_descricao].astype(str)

    temp["compra"] = temp["descricao_parcelamento"].apply(
        limpar_compra
    )

    temp["parcela_atual"] = temp["descricao_parcelamento"].apply(
        lambda x: extrair_parcela(x)[0]
    )

    temp["total_parcelas"] = temp["descricao_parcelamento"].apply(
        lambda x: extrair_parcela(x)[1]
    )

    parcelados = temp[
        temp["parcela_atual"].notna()
    ].copy()

    if len(parcelados) == 0:
        return pd.DataFrame()

    resultado = []

    for compra, grupo in parcelados.groupby("compra"):

        ultima_parcela = int(
            grupo["parcela_atual"].max()
        )

        total_parcelas = int(
            grupo["total_parcelas"].max()
        )

        linha = grupo[
            grupo["parcela_atual"] == ultima_parcela
        ].iloc[-1]

        valor_parcela = float(
            linha[coluna_valor]
        )

        parcelas_abertas = max(
            total_parcelas - ultima_parcela,
            0
        )

        valor_total_compra = (
            total_parcelas * valor_parcela
        )

        valor_pago = (
            ultima_parcela * valor_parcela
        )

        valor_restante = (
            parcelas_abertas * valor_parcela
        )

        status = (
            "QUITADO"
            if parcelas_abertas == 0
            else "ABERTO"
        )

        resultado.append({

            "compra": compra,

            "categoria": linha.get(
                "categoria",
                "Outros"
            ),

            "ultima_parcela": ultima_parcela,

            "total_parcelas": total_parcelas,

            "parcelas_pagas": ultima_parcela,

            "parcelas_abertas": parcelas_abertas,

            "valor_parcela": valor_parcela,

            "valor_total_compra": valor_total_compra,

            "valor_pago": valor_pago,

            "valor_restante": valor_restante,

            "status": status,

            "descricao_detectada": linha.get(
                coluna_descricao,
                ""
            )

        })

    resultado = pd.DataFrame(resultado)

    resultado = resultado.sort_values(
        "valor_restante",
        ascending=False
    )

    return resultado


# ============================================================
# RESUMO EXECUTIVO
# ============================================================

def resumo_parcelamentos(df_parcelamentos):

    if df_parcelamentos is None or len(df_parcelamentos) == 0:

        return {

            "parcelamentos": 0,
            "abertos": 0,
            "quitados": 0,
            "valor_restante": 0,
            "valor_total_compras": 0,
            "maior_compromisso": 0

        }

    abertos = df_parcelamentos[
        df_parcelamentos["status"] == "ABERTO"
    ]

    quitados = df_parcelamentos[
        df_parcelamentos["status"] == "QUITADO"
    ]

    return {

        "parcelamentos":
            len(df_parcelamentos),

        "abertos":
            len(abertos),

        "quitados":
            len(quitados),

        "valor_restante":
            float(
                df_parcelamentos[
                    "valor_restante"
                ].sum()
            ),

        "valor_total_compras":
            float(
                df_parcelamentos[
                    "valor_total_compra"
                ].sum()
            ),

        "maior_compromisso":
            float(
                df_parcelamentos[
                    "valor_restante"
                ].max()
            )

    }
