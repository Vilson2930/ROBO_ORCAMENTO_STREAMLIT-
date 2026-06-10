# ============================================================
# patterns.py
# ORÇAMENTO INTELIGENTE
# Biblioteca Central de Padrões
# ============================================================

import re

# ============================================================
# MESES
# ============================================================

MESES = {
    "jan": "01",
    "janeiro": "01",

    "fev": "02",
    "fevereiro": "02",

    "mar": "03",
    "marco": "03",
    "março": "03",

    "abr": "04",
    "abril": "04",

    "mai": "05",
    "maio": "05",

    "jun": "06",
    "junho": "06",

    "jul": "07",
    "julho": "07",

    "ago": "08",
    "agosto": "08",

    "set": "09",
    "setembro": "09",

    "out": "10",
    "outubro": "10",

    "nov": "11",
    "novembro": "11",

    "dez": "12",
    "dezembro": "12",
}

# ============================================================
# BLACKLIST
# ============================================================

BLACKLIST = [

    "DESPESAS DA FATURA",
    "DESPESAS DO MES",
    "DESPESAS DO MÊS",

    "TOTAL DA FATURA",
    "VALOR TOTAL DA FATURA",
    "TOTAL A PAGAR",

    "PAGAMENTO",
    "PAGAMENTO TOTAL",
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "PAGAMENTO ONLINE",
    "PAGAMENTO ON LINE",
    "PAGAMENTO PIX",
    "PAGAMENTO BOLETO",

    "PIX",
    "BOLETO",

    "ROTATIVO",
    "ENCARGOS",
    "ENCARGOS FINANCEIROS",

    "LIMITE",
    "VENCIMENTO",
    "FECHAMENTO",
    "MELHOR DIA",

    "SALDO",
    "CRÉDITO",
    "CREDITO",
    "ESTORNO",

    "PAGINA",
    "PÁGINA",

    "RESUMO",
    "FATURA",
]

# ============================================================
# PADRÕES DE DATA
# ============================================================

PADRAO_DATA_CURTA = re.compile(
    r"\b\d{2}/\d{2}(?:/\d{4})?\b",
    re.IGNORECASE
)

PADRAO_DATA_NUMERICA = re.compile(
    r"""
    (?P<data>\d{2}/\d{2}(?:/\d{4})?)
    \s+
    (?P<descricao>.+?)
    \s+
    (?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})
    $
    """,
    re.IGNORECASE | re.VERBOSE
)

PADRAO_DATA_EXTENSO = re.compile(
    r"""
    (?P<dia>\d{1,2})
    \s+DE\s+
    (?P<mes>[A-ZÇ]+)
    \.?
    \s+
    (?P<ano>\d{4})
    \s+
    (?P<descricao>.+?)
    \s+
    (?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})
    $
    """,
    re.IGNORECASE | re.VERBOSE
)

# ============================================================
# PADRÕES DE VALORES
# ============================================================

PADRAO_VALOR_REAIS = re.compile(
    r"R\$\s*([\d\.]+,\d{2})",
    re.IGNORECASE
)

PADRAO_VALOR_SIMPLES = re.compile(
    r"\d{1,3}(?:\.\d{3})*,\d{2}"
)

# ============================================================
# PADRÕES DE PARCELAMENTO
# (os mais comuns - a expansão fica no parcel_patterns.py)
# ============================================================

PADRAO_NX_DE = re.compile(
    r"""
    (?P<qtd>\d{1,2})
    \s*X\s*
    DE
    \s*
    R?\$?
    \s*
    (?P<valor>[\d\.]+,\d{2})
    """,
    re.IGNORECASE | re.VERBOSE
)

PADRAO_EM_NX = re.compile(
    r"""
    EM
    \s*
    (?P<qtd>\d{1,2})
    \s*
    X
    """,
    re.IGNORECASE | re.VERBOSE
)

PADRAO_NX = re.compile(
    r"""
    (?P<qtd>\d{1,2})
    \s*
    X
    """,
    re.IGNORECASE | re.VERBOSE
)

# ============================================================
# PADRÕES AUXILIARES
# ============================================================

PADRAO_ESPACOS = re.compile(r"\s+")

PADRAO_MULTIPLOS_ASTERISCOS = re.compile(r"\*+")

PADRAO_NUMERO = re.compile(r"\d+")

PADRAO_SO_DIGITOS = re.compile(r"^\d+$")

PADRAO_SO_LETRAS = re.compile(r"^[A-ZÀ-Ú\s]+$", re.IGNORECASE)
