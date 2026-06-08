# ============================================================
# CATEGORY ENGINE
# ORÇAMENTO INTELIGENTE
# Versão comercial genérica
# ============================================================

import re
import unicodedata
import pandas as pd


def normalizar_texto(texto):
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


REGRAS_CATEGORIAS = {

    "Combustível": [
        "POSTO", "AUTO POSTO", "COMBUSTIVEL", "GASOLINA",
        "ETANOL", "DIESEL", "IPIRANGA", "SHELL", "PETROBRAS",
        "ALE ", "RAIZEN"
    ],

    "Supermercado": [
        "SUPERMERCADO", "MERCADO", "MERCEARIA", "ATACADO",
        "ATACADAO", "ASSAI", "CARREFOUR", "EXTRA", "BIG",
        "CONDOR", "MUFFATO", "SUPERPAO", "HORTIFRUTI",
        "HORTI", "EMPORIO", "ALIMENTOS"
    ],

    "Alimentação fora de casa": [
        "RESTAURANTE", "RESTAUR", "LANCH", "LANCHONETE",
        "PIZZARIA", "PIZZA", "BURGER", "HAMBURGUER",
        "IFOOD", "UBER EATS", "AIQFOME", "DELIVERY",
        "PADARIA", "PANIFICADORA", "CONFEITARIA",
        "CAFE", "COFFEE", "SORVETE", "PASTEL",
        "CHURRASCARIA", "GRILL", "CANTINA", "BAR "
    ],

    "Saúde": [
        "FARMACIA", "DROGARIA", "DROGA", "DROGASIL",
        "RAIA", "PACHECO", "PANVEL", "CLINICA",
        "HOSPITAL", "LABORATORIO", "EXAME", "ODONTO",
        "DENTISTA", "MEDICO", "MEDICA", "OTICA",
        "ACADEMIA", "SMART FIT", "BIO RITMO", "BLUEFIT"
    ],

    "Transporte": [
        "UBER", "99", "TAXI", "CABIFY", "PASSAGEM",
        "METRO", "ONIBUS", "ÔNIBUS", "PEDAGIO",
        "ESTACIONAMENTO", "PARKING", "LOCADORA",
        "LOCALIZA", "MOVIDA", "UNIDAS"
    ],

    "Casa / Utilidades": [
        "HOME CENTER", "CONSTRUCAO", "CONSTRUÇÃO", "MATERIAL",
        "FERRAGEM", "PARAFUSO", "TINTAS", "MOVEIS",
        "MÓVEIS", "ELETRO", "UTILIDADES", "CASA",
        "LEROY", "TELHANORTE", "TOK STOK", "CAMICADO",
        "MAGAZINE LUIZA", "MAGALU"
    ],

    "Vestuário / Compras": [
        "MODAS", "ROUPAS", "VESTUARIO", "VESTUÁRIO",
        "CALCADOS", "CALÇADOS", "SAPATARIA", "TENIS",
        "TÊNIS", "RENNER", "RIACHUELO", "C A ",
        "CEA", "MARISA", "ZARA", "SHEIN", "SHOPEE",
        "MERCADO LIVRE", "AMERICANAS", "HAVAN",
        "PRIVALIA", "LOJA", "STORE", "SHOPPING"
    ],

    "Assinaturas / Digital": [
        "NETFLIX", "SPOTIFY", "AMAZON PRIME", "AMAZON DIGITAL",
        "GOOGLE", "APPLE", "MICROSOFT", "YOUTUBE",
        "DISNEY", "HBO", "MAX", "GLOBOPLAY",
        "CHATGPT", "OPENAI", "CANVA", "ADOBE"
    ],

    "Educação": [
        "ESCOLA", "COLEGIO", "COLÉGIO", "FACULDADE",
        "UNIVERSIDADE", "CURSO", "EDUCACAO", "EDUCAÇÃO",
        "LIVRARIA", "MATERIAL ESCOLAR", "UDEMY", "ALURA"
    ],

    "Lazer / Viagens": [
        "HOTEL", "POUSADA", "AIRBNB", "BOOKING",
        "DECOLAR", "CVC", "CINEMA", "CINE",
        "INGRESSO", "EVENTO", "SHOW", "TEATRO",
        "PARQUE", "CLUBE", "BAR", "DRINKS"
    ],

    "Serviços / Pagamentos pessoais": [
        "BARBEARIA", "SALAO", "SALÃO", "BELEZA",
        "MANICURE", "LAVANDERIA", "LAVA JATO",
        "SERVICOS", "SERVIÇOS", "CONSULTORIA",
        "PIX", "TRANSFERENCIA", "TRANSFERÊNCIA",
        "PAGAMENTO", "MAXISCARD"
    ],

    "Pagamentos / Intermediadores": [
        "MERCADO PAGO", "PICPAY", "PAGSEGURO", "GETNET",
        "STONE", "CIELO", "REDE", "SUMUP", "TON",
        "MP ", "BLU INSTITUICAO", "INSTITUICAO DE PAG"
    ],

    "Documentação / Impostos": [
        "CARTORIO", "CARTÓRIO", "DETRAN", "PREFEITURA",
        "IPVA", "MULTA", "TRIBUTO", "IMPOSTO",
        "TAXA", "RECEITA FEDERAL"
    ],

    "Pets": [
        "PET", "PETZ", "COBASI", "VETERINARIO",
        "VETERINÁRIO", "RACAO", "RAÇÃO", "AGROPECUARIA"
    ],
}


def classificar_categoria(merchant):

    texto = normalizar_texto(merchant)

    for categoria, palavras in REGRAS_CATEGORIAS.items():
        for palavra in palavras:
            palavra_norm = normalizar_texto(palavra)
            if palavra_norm in texto:
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
            columns=["valor_total", "quantidade", "ticket_medio", "percentual_total"]
        )

    if "categoria" not in df.columns:
        df = processar_categorias(df)

    valor_total = df["valor"].sum()

    resumo = (
        df
        .groupby("categoria")
        .agg(
            valor_total=("valor", "sum"),
            quantidade=("valor", "count"),
            ticket_medio=("valor", "mean")
        )
        .sort_values("valor_total", ascending=False)
    )

    resumo["percentual_total"] = (
        resumo["valor_total"] / valor_total * 100
        if valor_total > 0
        else 0
    )

    return resumo


def auditar_outros(df, top=30):

    if df is None or len(df) == 0:
        return pd.DataFrame(
            columns=["valor_total", "quantidade", "ticket_medio"]
        )

    if "categoria" not in df.columns:
        df = processar_categorias(df)

    outros = df[df["categoria"] == "Outros"]

    if len(outros) == 0:
        return pd.DataFrame(
            columns=["valor_total", "quantidade", "ticket_medio"]
        )

    return (
        outros
        .groupby("merchant")
        .agg(
            valor_total=("valor", "sum"),
            quantidade=("valor", "count"),
            ticket_medio=("valor", "mean")
        )
        .sort_values("valor_total", ascending=False)
        .head(top)
    )


def resumo_category_engine(df):

    resumo = resumo_categorias(df)

    if resumo is None or len(resumo) == 0:
        return {
            "total_categorias": 0,
            "valor_total": 0,
            "valor_outros": 0,
            "percentual_outros": 0,
            "status": "SEM DADOS"
        }

    valor_total = float(resumo["valor_total"].sum())

    valor_outros = 0
    if "Outros" in resumo.index:
        valor_outros = float(resumo.loc["Outros", "valor_total"])

    percentual_outros = (
        valor_outros / valor_total * 100
        if valor_total > 0
        else 0
    )

    if percentual_outros <= 10:
        status = "APROVADO"
    elif percentual_outros <= 15:
        status = "ACEITÁVEL"
    else:
        status = "PRECISA REFINAR"

    return {
        "total_categorias": len(resumo),
        "valor_total": valor_total,
        "valor_outros": valor_outros,
        "percentual_outros": percentual_outros,
        "status": status
    }
