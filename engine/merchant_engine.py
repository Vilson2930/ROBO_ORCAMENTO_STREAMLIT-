# ============================================================
# MERCHANT ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

import re
import pandas as pd

# ============================================================
# LIMPEZA DE NOMES
# ============================================================

def limpar_merchant(texto):

    texto = str(texto).upper()

    texto = re.sub(
        r"\(PARCELA\s*\d+\s*DE\s*\d+\)",
        "",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    texto = texto.strip()

    return texto


# ============================================================
# IDENTIFICAR MERCHANT
# ============================================================

def identificar_merchant(descricao):

    descricao = limpar_merchant(descricao)

    return descricao


# ============================================================
# PROCESSAR MERCHANTS
# ============================================================

def processar_merchants(df):

    if len(df) == 0:
        return df

    df = df.copy()

    df["merchant"] = df[
        "descricao_original"
    ].apply(
        identificar_merchant
    )

    return df


# ============================================================
# RESUMO POR MERCHANT
# ============================================================

def resumo_merchants(df):

    if len(df) == 0:
        return pd.DataFrame()

    resumo = (

        df
        .groupby("merchant")
        .agg(

            valor_total=("valor", "sum"),

            quantidade=("valor", "count"),

            ticket_medio=("valor", "mean")

        )

    )

    resumo["percentual_total"] = (

        resumo["valor_total"]

        / resumo["valor_total"].sum()

        * 100

    )

    resumo["percentual_acumulado"] = (

        resumo["percentual_total"]

        .cumsum()

    )

    resumo = (

        resumo

        .sort_values(
            "valor_total",
            ascending=False
        )

    )

    return resumo


# ============================================================
# TOP DESTINOS DO DINHEIRO
# ============================================================

def top_merchants(df, top=50):

    resumo = resumo_merchants(df)

    return resumo.head(top)


# ============================================================
# RESUMO EXECUTIVO
# ============================================================

def resumo_merchant_engine(df):

    resumo = resumo_merchants(df)

    if len(resumo) == 0:

        return {

            "total_merchants": 0,
            "valor_total": 0

        }

    return {

        "total_merchants": len(resumo),

        "valor_total": float(
            resumo["valor_total"].sum()
        )

    }
