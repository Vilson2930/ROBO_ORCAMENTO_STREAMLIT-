# ============================================================
# CATEGORY ENGINE
# ORÇAMENTO INTELIGENTE
# Versão comercial com aprendizado via user_rules.csv
# ============================================================

import re
import unicodedata
from pathlib import Path
import pandas as pd


USER_RULES_PATH = Path("data/user_rules.csv")


def normalizar_texto(texto):
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def carregar_regras_usuario():
    if not USER_RULES_PATH.exists():
        return []

    try:
        df = pd.read_csv(USER_RULES_PATH)

        if df.empty:
            return []

        if "merchant" not in df.columns or "categoria" not in df.columns:
            return []

        regras = []

        for _, row in df.iterrows():
            merchant = normalizar_texto(row.get("merchant", ""))
            categoria = str(row.get("categoria", "")).strip()

            if merchant and categoria:
                regras.append((merchant, categoria))

        return regras

    except Exception:
        return []


REGRAS_CATEGORIAS = {

    "Combustível": [
        "POSTO", "AUTO POSTO", "REDE DE POSTOS", "COMBUSTIVEL",
        "COMBUSTÍVEL", "GASOLINA", "ETANOL", "DIESEL", "FLEX",
        "IPIRANGA", "SHELL", "PETROBRAS", "VIBRA", "RAIZEN",
        "ALE", "BR MANIA", "TEXACO", "PETRO", "ABASTECE",
        "ABASTECIMENTO", "COMERCIO DE COMB"
    ],

    "Supermercado": [
        "SUPERMERCADO", "SUPERMERCAD", "MERCADO", "MERCEARIA",
        "MINI MERCADO", "ATACADO", "ATACADAO", "ATACADÃO",
        "ASSAI", "ASSAÍ", "CARREFOUR", "EXTRA", "BIG",
        "WALMART", "MUFFATO", "CONDOR", "FORT", "MAXXI",
        "COMPER", "MATEUS", "SUPERPAO", "SUPERPÃO",
        "HORTIFRUTI", "HORTI", "EMPORIO", "EMPÓRIO",
        "ALIMENTOS", "COMERCIO DE ALIMEN", "CESTA", "SACOLAO",
        "SACOLÃO", "QUITANDA", "VERDURAO", "VERDURÃO",
        "AÇOUGUE", "ACOUGUE"
    ],

    "Alimentação fora de casa": [
        "RESTAURANTE", "RESTAUR", "REST ", "LANCH", "LANCHONETE",
        "LANCHES", "PIZZARIA", "PIZZA", "BURGER", "HAMBURGUER",
        "HAMBURGUERIA", "IFOOD", "UBER EATS", "RAPPI", "AIQFOME",
        "DELIVERY", "PADARIA", "PANIFICADORA", "PANIF",
        "CONFEITARIA", "CAFE", "CAFÉ", "COFFEE", "SORVETE",
        "SORVETERIA", "PASTEL", "PASTELARIA", "CHURRASCARIA",
        "GRILL", "CANTINA", "BAR", "PUB", "BISTRO", "ESFIHA",
        "SUSHI", "TEMAKERIA", "AÇAÍ", "ACAI", "COZINHA",
        "MARMITA", "MARMITARIA", "DOCERIA", "BOLOS", "BOLO",
        "CHOCOLATE", "MALTE", "GASTRONOM", "FEIJOADA",
        "CONVENIENCIA", "CARNE", "BEEF", "BURGUES", "BUFFALO"
    ],

    "Saúde": [
        "FARMACIA", "FARMÁCIA", "FARMACEUTICA", "FARMACÊUTICA",
        "DROGARIA", "DROGA", "DROGASIL", "RAIA", "PACHECO",
        "PANVEL", "NISSEI", "CLINICA", "CLÍNICA", "HOSPITAL",
        "LABORATORIO", "LABORATÓRIO", "LAB ", "EXAME", "EXAMES",
        "ODONTO", "ODONTOLOGIA", "DENTISTA", "MEDICO", "MÉDICO",
        "MEDICA", "MÉDICA", "CONSULTORIO", "CONSULTÓRIO",
        "OTICA", "ÓTICA", "OFTALMO", "CARDIO", "DERMATO",
        "FISIOTERAPIA", "FISIO", "PSICOLOGIA", "TERAPIA",
        "ACADEMIA", "SMART FIT", "BIO RITMO", "BLUEFIT", "GYM",
        "FITNESS", "CROSSFIT", "MUSCULACAO", "MUSCULAÇÃO",
        "FORMULAS", "FORMULAS", "DRA ", "DR "
    ],

    "Transporte": [
        "UBER", "99", "TAXI", "TÁXI", "CABIFY", "PASSAGEM",
        "METRO", "METRÔ", "ONIBUS", "ÔNIBUS", "RODOVIARIA",
        "RODOVIÁRIA", "PEDAGIO", "PEDÁGIO", "ESTACIONAMENTO",
        "PARKING", "LOCADORA", "LOCALIZA", "MOVIDA", "UNIDAS",
        "SEM PARAR", "CONECTCAR", "VELOE", "RENT A CAR"
    ],

    "Casa / Utilidades": [
        "HOME CENTER", "CONSTRUCAO", "CONSTRUÇÃO", "MATERIAL",
        "MATERIAL DE CONSTRUCAO", "MATERIAL DE CONSTRUÇÃO",
        "FERRAGEM", "FERRAGENS", "PARAFUSO", "PARAFUSOS",
        "TINTAS", "TINTA", "MOVEIS", "MÓVEIS", "ELETRO",
        "ELETRODOMESTICO", "ELETRODOMÉSTICO", "UTILIDADES",
        "CASA", "LEROY", "LEROY MERLIN", "TELHANORTE", "CASSOL",
        "TOK STOK", "TOKSTOK", "CAMICADO", "DECOR", "DECORACAO",
        "DECORAÇÃO", "MADEIRA", "MDF", "ILUMINACAO", "ILUMINAÇÃO",
        "MAGAZINE LUIZA", "MAGALU", "CASAS BAHIA", "PONTO FRIO",
        "FAST SHOP", "PONTO DAS CAPAS", "GMAD", "BORTOLANZA"
    ],

    "Vestuário / Compras": [
        "MODAS", "ROUPAS", "VESTUARIO", "VESTUÁRIO", "CALCADOS",
        "CALÇADOS", "SAPATARIA", "TENIS", "TÊNIS", "RENNER",
        "RIACHUELO", "MARISA", "CEA", "C A", "C&A", "ZARA",
        "SHEIN", "SHOPEE", "MERCADO LIVRE", "AMERICANAS", "HAVAN",
        "PRIVALIA", "LOJA", "STORE", "SHOPPING", "CENTER",
        "BOUTIQUE", "OUTLET", "CONFEC", "CONFECCAO", "CONFECÇÃO",
        "COSMETICOS", "COSMÉTICOS", "PERFUMARIA", "BELEZA",
        "O BOTICARIO", "BOTICARIO", "NATURA", "AVON", "SEPHORA",
        "DAFITI", "NETSHOES", "CENTAURO", "DECATHLON", "ZZOPER"
    ],

    "Assinaturas / Digital": [
        "NETFLIX", "SPOTIFY", "AMAZON PRIME", "AMAZON DIGITAL",
        "GOOGLE", "APPLE", "MICROSOFT", "YOUTUBE", "DISNEY",
        "DISNEY PLUS", "HBO", "MAX", "GLOBOPLAY", "PARAMOUNT",
        "STARPLUS", "STAR PLUS", "CHATGPT", "OPENAI", "CANVA",
        "ADOBE", "DROPBOX", "ICLOUD", "ONE DRIVE", "ONEDRIVE",
        "NORTON", "AVAST", "KASPERSKY", "HOSTINGER", "GODADDY",
        "DOMAIN", "DOMINIO", "DOMÍNIO"
    ],

    "Educação": [
        "ESCOLA", "COLEGIO", "COLÉGIO", "FACULDADE", "UNIVERSIDADE",
        "CURSO", "EDUCACAO", "EDUCAÇÃO", "LIVRARIA", "MATERIAL ESCOLAR",
        "UDEMY", "ALURA", "HOTMART", "EDUZZ", "KIRVANO", "KIWIFY",
        "COURSERA", "DOMESTIKA", "EAD", "APOSTILA", "LIVRO",
        "ASSOCIACAODEPAISE", "ASSOCIACAO DE PAIS"
    ],

    "Lazer / Viagens": [
        "HOTEL", "POUSADA", "AIRBNB", "BOOKING", "DECOLAR", "CVC",
        "AZUL", "GOL", "LATAM", "PASSAREDO", "CINEMA", "CINE",
        "INGRESSO", "INGRESSO COM", "EVENTO", "EVENTOS", "SHOW",
        "TEATRO", "PARQUE", "CLUBE", "DRINKS", "BALADA", "FESTA",
        "TURISMO", "VIAGEM", "VIAGENS", "RESORT", "MOTORSPORT",
        "RACING"
    ],

    "Serviços / Pagamentos pessoais": [
        "BARBEARIA", "SALAO", "SALÃO", "CABELEIREIRO", "MANICURE",
        "PEDICURE", "LAVANDERIA", "LAVA JATO", "SERVICOS", "SERVIÇOS",
        "CONSULTORIA", "MANUTENCAO", "MANUTENÇÃO", "REPARO",
        "ASSISTENCIA", "ASSISTÊNCIA", "OFICINA", "MECANICA", "MECÂNICA",
        "CHAVEIRO", "COSTURA", "ALFAIATE", "CUIDADOR", "DIARISTA",
        "LAVO", "AYUB", "BONFIM", "AUGUSTO", "JOHN", "LEONARDO",
        "LUCASLUIZ", "VINICIUS", "BRENO", "NELSON", "VITORHENRIQUE",
        "LILIANE", "MARIA"
    ],

    "Pagamentos / Intermediadores": [
        "MERCADO PAGO", "PICPAY", "PAGSEGURO", "GETNET", "STONE",
        "CIELO", "REDE", "SUMUP", "TON", "MP ", "BLU INSTITUICAO",
        "INSTITUICAO DE PAG", "INSTITUIÇÃO DE PAG", "ADIQ", "MAXISCARD",
        "PAYPAL", "EBANX", "ASAAS", "IUGU", "PAGAR ME", "PAGARME",
        "PG ", "JIM COM", "JIM.COM", "ZIG"
    ],

    "Documentação / Impostos": [
        "CARTORIO", "CARTÓRIO", "DETRAN", "PREFEITURA", "IPVA",
        "MULTA", "TRIBUTO", "IMPOSTO", "TAXA", "RECEITA FEDERAL",
        "DARF", "GUIA", "LICENCIAMENTO", "REGISTRO CIVIL"
    ],

    "Pets": [
        "PET", "PETZ", "COBASI", "VETERINARIO", "VETERINÁRIO",
        "VETERINARIA", "VETERINÁRIA", "RACAO", "RAÇÃO",
        "AGROPECUARIA", "AGROPECUÁRIA", "BANHO E TOSA", "TOSA"
    ],

    "Financeiro / Bancário": [
        "SEGURO", "SEGURADORA", "PREVIDENCIA", "PREVIDÊNCIA",
        "CONSORCIO", "CONSÓRCIO", "BANCO", "FINANCEIRA",
        "CARTAO", "CARTÃO", "ANUIDADE", "JUROS", "ENCARGOS"
    ],
}


def classificar_por_user_rules(texto):
    regras = carregar_regras_usuario()

    for merchant_regra, categoria in regras:
        if merchant_regra in texto:
            return categoria

    return None


def classificar_categoria(merchant):
    texto = normalizar_texto(merchant)

    if not texto:
        return "Outros"

    categoria_usuario = classificar_por_user_rules(texto)

    if categoria_usuario:
        return categoria_usuario

    for categoria, palavras in REGRAS_CATEGORIAS.items():
        for palavra in palavras:
            palavra_norm = normalizar_texto(palavra)

            if not palavra_norm:
                continue

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

    if percentual_outros <= 5:
        status = "EXCELENTE"
    elif percentual_outros <= 10:
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
