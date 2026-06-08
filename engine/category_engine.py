# ============================================================
# CATEGORY ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

import pandas as pd

# ============================================================
# DICIONÁRIO DE CATEGORIAS
# ============================================================

CATEGORIAS = {

    # --------------------------------------------------------
    # COMBUSTÍVEL
    # --------------------------------------------------------

    "POSTO": "Combustível",
    "COMBUSTIVEL": "Combustível",
    "IPIRANGA": "Combustível",
    "SHELL": "Combustível",
    "PETROBRAS": "Combustível",

    # --------------------------------------------------------
    # SUPERMERCADO
    # --------------------------------------------------------

    "SUPERMERCADO": "Supermercado",
    "SUPERPAO": "Supermercado",
    "MERCADO": "Supermercado",
    "ATACADAO": "Supermercado",

    # --------------------------------------------------------
    # ALIMENTAÇÃO
    # --------------------------------------------------------

    "RESTAURANTE": "Alimentação fora de casa",
    "LANCHES": "Alimentação fora de casa",
    "PIZZARIA": "Alimentação fora de casa",
    "GRILL": "Alimentação fora de casa",
    "CANTINA": "Alimentação fora de casa",
    "FEIJOADA": "Alimentação fora de casa",

    # --------------------------------------------------------
    # SAÚDE
    # --------------------------------------------------------

    "FARMACIA": "Saúde",
    "FARMACEUTICA": "Saúde",
    "LABORATORIO": "Saúde",
    "OTICAS": "Saúde",
    "FORMULAS": "Saúde",
    "DRA": "Saúde",

    # --------------------------------------------------------
    # TECNOLOGIA
    # --------------------------------------------------------

    "TECNOLOGIA": "Tecnologia",
    "INFO": "Tecnologia",
    "ELETRONICOS": "Tecnologia",

    # --------------------------------------------------------
    # CASA
    # --------------------------------------------------------

    "HOME CENTER": "Casa / Utilidades",
    "DAL POZZO": "Casa / Utilidades",
    "ELETRO": "Casa / Utilidades",

    # --------------------------------------------------------
    # VESTUÁRIO
    # --------------------------------------------------------

    "PRIVALIA": "Vestuário / Compras",
    "ZZOPER": "Vestuário / Compras",
    "HAVAN": "Vestuário / Compras",
    "MODAS": "Vestuário / Compras",
    "CONFECCOES": "Vestuário / Compras",

    # --------------------------------------------------------
    # SERVIÇOS
    # --------------------------------------------------------

    "MAXISCARD": "Serviços / Pagamentos pessoais",
    "BARBOSA": "Serviços / Pagamentos pessoais",

    # --------------------------------------------------------
    # INTERMEDIADORES
    # --------------------------------------------------------

    "MP ": "Pagamentos / Intermediadores",
    "MERCADO PAGO": "Pagamentos / Intermediadores",
    "ADIQ": "Pagamentos / Intermediadores",

}

# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classificar_categoria(merchant):

    merchant = str(merchant).upper()

    for chave, categoria in CATEGORIAS.items():

        if chave in merchant:
            return categoria

    return "Outros"


# ============================================================
# PROCESSAR CATEGORIAS
# ============================================================

def processar_categorias(df):

    if len(df) == 0:
        return df

    df = df.copy()

    df["categoria"] = (

        df["merchant"]

        .apply(
            classificar_categoria
        )

    )

    return df


# ============================================================
# RESUMO CATEGORIAS
# ============================================================

def resumo_categorias(df):

    if len(df) == 0:
        return pd.DataFrame()

    resumo = (

        df

        .groupby("categoria")

        .agg(

            valor_total=("valor", "sum"),

            quantidade=("valor", "count")

        )

    )

    resumo["percentual_total"] = (

        resumo["valor_total"]

        / resumo["valor_total"].sum()

        * 100

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
# RESUMO EXECUTIVO
# ============================================================

def resumo_category_engine(df):

    resumo = resumo_categorias(df)

    if len(resumo) == 0:

        return {

            "total_categorias": 0,
            "valor_total": 0

        }

    return {

        "total_categorias": len(resumo),

        "valor_total": float(
            resumo["valor_total"].sum()
        )

    }
