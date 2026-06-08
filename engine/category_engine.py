# ============================================================
# CATEGORY ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

import re
import unicodedata
import pandas as pd


def normalizar_texto(texto):
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto)
    return texto


CATEGORIAS = {

    # COMBUSTÍVEL
    "POSTO": "Combustível",
    "AUTO POSTO": "Combustível",
    "COMBUSTIVEL": "Combustível",
    "COMB": "Combustível",
    "IPIRANGA": "Combustível",
    "SHELL": "Combustível",
    "PETROBRAS": "Combustível",
    "CALED": "Combustível",
    "STAWS": "Combustível",
    "INDIO": "Combustível",
    "ROSETTI": "Combustível",
    "FERLIN": "Combustível",
    "REDEGUAPODEPOSTOS": "Combustível",
    "GUAPO": "Combustível",
    "PANDA AUTO": "Combustível",
    "PRA FRENTE": "Combustível",
    "IBEMA": "Combustível",

    # SUPERMERCADO
    "SUPERMERCADO": "Supermercado",
    "SUPERPAO": "Supermercado",
    "MERCADO": "Supermercado",
    "ATACADAO": "Supermercado",
    "CRUZ E CRUZ": "Supermercado",
    "REDE PARTEKA DE SUPERM": "Supermercado",
    "ALIMENTOS": "Supermercado",
    "ARMAZEM": "Supermercado",
    "ESPECIARIAS": "Supermercado",
    "EMPORIO": "Supermercado",
    "GIRASSOL": "Supermercado",
    "PANIF": "Supermercado",
    "PANIFICADORA": "Supermercado",
    "CONFEIT": "Supermercado",

    # ALIMENTAÇÃO FORA DE CASA
    "RESTAURANTE": "Alimentação fora de casa",
    "RESTAUR": "Alimentação fora de casa",
    "REST ": "Alimentação fora de casa",
    "LANCH": "Alimentação fora de casa",
    "PIZZ": "Alimentação fora de casa",
    "GRILL": "Alimentação fora de casa",
    "CANTINA": "Alimentação fora de casa",
    "FEIJOADA": "Alimentação fora de casa",
    "SABOR": "Alimentação fora de casa",
    "MERUZA": "Alimentação fora de casa",
    "PORTO UBA": "Alimentação fora de casa",
    "GARAGEM": "Alimentação fora de casa",
    "TZ RESTAURANTE": "Alimentação fora de casa",
    "AROMA": "Alimentação fora de casa",
    "BOI NA BRASA": "Alimentação fora de casa",
    "GOCOFFEE": "Alimentação fora de casa",
    "COFFEE": "Alimentação fora de casa",
    "PICOLE": "Alimentação fora de casa",
    "BONTA": "Alimentação fora de casa",
    "D D PRENSADO": "Alimentação fora de casa",
    "NOVA PARADA HOTEL REST": "Alimentação fora de casa",

    # SAÚDE
    "FARMACIA": "Saúde",
    "FARMACEUTICA": "Saúde",
    "LABORATORIO": "Saúde",
    "OTICA": "Saúde",
    "FORMULA": "Saúde",
    "DRA": "Saúde",
    "DR ": "Saúde",
    "CARTAO DE TODOS": "Saúde",
    "REDE SAUDE": "Saúde",
    "HEVILLYN": "Saúde",
    "BATEL": "Saúde",

    # TECNOLOGIA / ASSINATURAS DIGITAIS
    "TECNOLOGIA": "Tecnologia",
    "INFO": "Tecnologia",
    "ELETRONIC": "Tecnologia",
    "JE TECNOLOGIA": "Tecnologia",
    "AMAZON DIGITAL": "Tecnologia",
    "AMAZON": "Tecnologia",

    # CASA / UTILIDADES
    "HOME CENTER": "Casa / Utilidades",
    "DAL POZZO": "Casa / Utilidades",
    "ELETRO": "Casa / Utilidades",
    "SCHULZE": "Casa / Utilidades",
    "PONTO DAS CAPAS": "Casa / Utilidades",
    "LAVO": "Casa / Utilidades",
    "ENCAPE": "Casa / Utilidades",
    "GMAD": "Casa / Utilidades",
    "BORTOLANZA": "Casa / Utilidades",

    # VESTUÁRIO / COMPRAS
    "PRIVALIA": "Vestuário / Compras",
    "PRI*PRIVALIA": "Vestuário / Compras",
    "ZZOPER": "Vestuário / Compras",
    "HAVAN": "Vestuário / Compras",
    "MODAS": "Vestuário / Compras",
    "ZARPELLON": "Vestuário / Compras",
    "SAPATARIA": "Vestuário / Compras",
    "NEWTON": "Vestuário / Compras",
    "CONFECC": "Vestuário / Compras",
    "COSMETICOS": "Vestuário / Compras",
    "DESTAK": "Vestuário / Compras",
    "YASMIN": "Vestuário / Compras",

    # SERVIÇOS / PAGAMENTOS PESSOAIS
    "MAXISCARD": "Serviços / Pagamentos pessoais",
    "MAXISCAR": "Serviços / Pagamentos pessoais",
    "BARBOSA": "Serviços / Pagamentos pessoais",
    "BARBEARIA": "Serviços / Pagamentos pessoais",
    "CAMARGO": "Serviços / Pagamentos pessoais",
    "BONFIM": "Serviços / Pagamentos pessoais",
    "JOHN": "Serviços / Pagamentos pessoais",
    "ALEXANDRE": "Serviços / Pagamentos pessoais",
    "LUCIANO": "Serviços / Pagamentos pessoais",
    "NELSON": "Serviços / Pagamentos pessoais",
    "AYUB": "Serviços / Pagamentos pessoais",
    "AUGUSTO": "Serviços / Pagamentos pessoais",
    "MARCUSWILLIAN": "Serviços / Pagamentos pessoais",

    # INTERMEDIADORES
    "MERCADO PAGO": "Pagamentos / Intermediadores",
    "MP ": "Pagamentos / Intermediadores",
    "ADIQ": "Pagamentos / Intermediadores",
    "BLU INSTITUICAO": "Pagamentos / Intermediadores",
    "PG ": "Pagamentos / Intermediadores",
    "PICPAY": "Pagamentos / Intermediadores",

    # LAZER / EVENTOS
    "EVENTO": "Lazer / Eventos",
    "PSYBAR": "Lazer / Eventos",
    "PSY BAR": "Lazer / Eventos",
    "MALTE": "Lazer / Eventos",
    "CONVENIENCIA": "Lazer / Eventos",
    "HELP CONVENIENCIA": "Lazer / Eventos",
    "PALOMASDRINKS": "Lazer / Eventos",
    "DRINKS": "Lazer / Eventos",
    "ALLE": "Lazer / Eventos",

    # VIAGEM / HOSPEDAGEM
    "HOTEL": "Viagem / Hospedagem",
    "PAX EXPRESS": "Viagem / Hospedagem",
}


def classificar_categoria(merchant):

    merchant_norm = normalizar_texto(merchant)

    for chave, categoria in CATEGORIAS.items():
        chave_norm = normalizar_texto(chave)

        if chave_norm in merchant_norm:
            return categoria

    return "Outros"


def processar_categorias(df):

    if df is None or len(df) == 0:
        return df

    df = df.copy()

    if "merchant" not in df.columns:
        df["merchant"] = df["descricao_original"]

    df["categoria"] = df["merchant"].apply(classificar_categoria)

    return df


def resumo_categorias(df):

    if df is None or len(df) == 0:
        return pd.DataFrame(
            columns=["valor_total", "quantidade", "percentual_total"]
        )

    if "categoria" not in df.columns:
        df = processar_categorias(df)

    resumo = (
        df
        .groupby("categoria")
        .agg(
            valor_total=("valor", "sum"),
            quantidade=("valor", "count")
        )
        .sort_values("valor_total", ascending=False)
    )

    total = resumo["valor_total"].sum()

    if total > 0:
        resumo["percentual_total"] = resumo["valor_total"] / total * 100
    else:
        resumo["percentual_total"] = 0

    return resumo


def resumo_category_engine(df):

    resumo = resumo_categorias(df)

    if resumo is None or len(resumo) == 0:
        return {
            "total_categorias": 0,
            "valor_total": 0
        }

    return {
        "total_categorias": len(resumo),
        "valor_total": float(resumo["valor_total"].sum())
    }
