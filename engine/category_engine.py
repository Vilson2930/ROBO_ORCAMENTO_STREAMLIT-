# ============================================================
# CATEGORY ENGINE
# ORÇAMENTO INTELIGENTE
# Baseado na Célula 6 - Category Engine por Valor V2
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


def classificar_categoria(merchant):

    m = normalizar_texto(merchant)

    # ========================================================
    # COMBUSTÍVEL
    # ========================================================

    if any(x in m for x in [
        "POSTO", "AUTO POSTO", "COMBUSTIVEL", "COMB", "STAWS",
        "ROSETTI", "CALED", "INDIO", "GUAPO", "PANDA AUTO",
        "IBEMA", "FERLIN", "PRA FRENTE"
    ]):
        return "Combustível"

    # ========================================================
    # SUPERMERCADO
    # ========================================================

    if any(x in m for x in [
        "SUPERPAO", "SUPERMERCADO", "CRUZ E CRUZ", "ALIMENTOS",
        "EMPORIO GIRASSOL", "CASA DE ESPECIARIAS",
        "PMV COMERCIO DE ALIMEN", "REDE PARTEKA DE SUPERM"
    ]):
        return "Supermercado"

    # ========================================================
    # ALIMENTAÇÃO FORA DE CASA
    # ========================================================

    if any(x in m for x in [
        "RESTAURANTE", "RESTAUR", "REST", "MERUZA",
        "TZ RESTAURANTE", "GARAGEM", "CANTINA", "FEIJOADA",
        "PARTEKA", "ARMAZEM DO MALTE", "SABOR IRRESISTIVEL",
        "PANIF", "PANIFICADORA", "FAMILIA SOUZA", "DOM HENRIQUE",
        "GASTRONOM", "ALLE CONVENIENCIA", "GOCOFFEE", "PICOLE",
        "BOI NA BRASA", "AROMA SABOR", "CHALE COLONIAL",
        "COSTENA", "D D PRENSADO"
    ]):
        return "Alimentação fora de casa"

    # ========================================================
    # VESTUÁRIO / COMPRAS
    # ========================================================

    if any(x in m for x in [
        "ZZOPER", "PRIVALIA", "MODAS", "ZARPELLON", "STORE",
        "SHOPEE", "MERCADO LIVRE", "SAPATARIA", "COSMETICOS",
        "DESTAK", "YASMIN", "CONFECC"
    ]):
        return "Vestuário / Compras"

    # ========================================================
    # CASA / UTILIDADES
    # ========================================================

    if any(x in m for x in [
        "HOME CENTER", "DAL POZZO", "ELETRO", "SCHULZE",
        "PONTO DAS CAPAS", "GMAD", "BORTOLANZA", "ENCAPE",
        "PARAFUSOS", "PARAFUSOS GUARAPUAVA"
    ]):
        return "Casa / Utilidades"

    # ========================================================
    # SAÚDE / ATIVIDADE FÍSICA
    # ========================================================

    if any(x in m for x in [
        "FARM", "FORMULAS", "BATEL", "LABORATORIO",
        "CARTAO DE TODOS", "DRA FRANCIS", "HEVILLYN",
        "ADIQPLU LABORATORIO", "FARMACIAS REDE SAUDE",
        "OTICA", "ACADEMIA", "ACADEMIAVIGOR", "VIGOR"
    ]):
        return "Saúde"

    # ========================================================
    # ASSINATURAS
    # ========================================================

    if any(x in m for x in [
        "SPOTIFY", "NETFLIX", "AMAZON", "GOOGLE", "APPLE",
        "MICROSOFT", "CHATGPT"
    ]):
        return "Assinaturas"

    # ========================================================
    # LAZER / VIAGENS
    # ========================================================

    if any(x in m for x in [
        "CINEX", "CINE", "PSYBAREEVENTOS", "PSY BAR",
        "HOTEL", "PAX EXPRESS", "PALOMASDRINKS", "DRINKS",
        "EVENTOS", "EVENTO"
    ]):
        return "Lazer / Viagens"

    # ========================================================
    # DOCUMENTAÇÃO / IMPOSTOS
    # ========================================================

    if any(x in m for x in [
        "CARTORIO", "CARTORI", "PEX GUARAPUAVA", "DETRAN",
        "PREFEITURA"
    ]):
        return "Documentação / Impostos"

    # ========================================================
    # TECNOLOGIA
    # ========================================================

    if any(x in m for x in [
        "TECNOLOGIA", "PG JE TECNOLOGIA", "INFO"
    ]):
        return "Tecnologia"

    # ========================================================
    # SERVIÇOS / PAGAMENTOS PESSOAIS
    # ========================================================

    if any(x in m for x in [
        "AYUB", "A S BONFIM", "ALEXANDRE", "LUCIANO BARBOSA",
        "RENE BARBOSA", "AUGUSTODOSSANTOS", "AUGUSTO DOS SANTOS",
        "JOHN", "NELSON IGLECIAS", "MARCUSWILLIAN", "JOAOVITOR",
        "BARBEARIA", "CAMARGO", "BRENO ARAUJO", "LEONARDO",
        "VINICIUS", "VINICIUSSTELLEDOS", "LUCASLUIZ", "58723970LEONARDO",
        "58730161LUCASLUIZ", "A S BOMFIM", "BOMFIM"
    ]):
        return "Serviços / Pagamentos pessoais"

    # ========================================================
    # SERVIÇOS DOMÉSTICOS
    # ========================================================

    if any(x in m for x in [
        "LAVO GUARAPUAVA", "LAVO"
    ]):
        return "Serviços domésticos"

    # ========================================================
    # PAGAMENTOS / INTERMEDIADORES
    # ========================================================

    if any(x in m for x in [
        "PG MAXISCARD", "MAXISCARD", "MP CAMILEARISTID",
        "MP *CAMILEARISTID", "CAMILEARISTID", "MERCADO PAGO",
        "PICPAY", "BLU INSTITUICAO"
    ]):
        return "Pagamentos / Intermediadores"

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

    if valor_total > 0:
        resumo["percentual_total"] = resumo["valor_total"] / valor_total * 100
    else:
        resumo["percentual_total"] = 0

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

    auditoria = (
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

    return auditoria


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

    percentual_outros = (valor_outros / valor_total * 100) if valor_total > 0 else 0

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
