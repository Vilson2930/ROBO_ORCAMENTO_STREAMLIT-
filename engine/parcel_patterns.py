# ============================================================
# parcel_patterns.py
# ORÇAMENTO INTELIGENTE
# Biblioteca Nacional de Parcelamentos
# ============================================================

import re

# ============================================================
# PARCELA 01 DE 06
# PARCELA 1 DE 6
# ============================================================

PADRAO_PARCELA_DE = re.compile(
    r"""
    PARCELA
    \s*
    (?P<atual>\d{1,2})
    \s*
    DE
    \s*
    (?P<total>\d{1,2})
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# PARC 01 DE 06
# PARC. 01 DE 06
# ============================================================

PADRAO_PARC_DE = re.compile(
    r"""
    PARC\.?
    \s*
    (?P<atual>\d{1,2})
    \s*
    DE
    \s*
    (?P<total>\d{1,2})
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# PARC 01/06
# PARC. 01/06
# ============================================================

PADRAO_PARC_BARRA = re.compile(
    r"""
    PARC\.?
    \s*
    (?P<atual>\d{1,2})
    /
    (?P<total>\d{1,2})
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# PARCELA 01/06
# ============================================================

PADRAO_PARCELA_BARRA = re.compile(
    r"""
    PARCELA
    \s*
    (?P<atual>\d{1,2})
    /
    (?P<total>\d{1,2})
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# 01/06
# 1/6
# ============================================================

PADRAO_BARRA = re.compile(
    r"""
    \b
    (?P<atual>\d{1,2})
    /
    (?P<total>\d{1,2})
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# 01 DE 06
# 1 DE 6
# ============================================================

PADRAO_DE = re.compile(
    r"""
    \b
    (?P<atual>\d{1,2})
    \s*
    DE
    \s*
    (?P<total>\d{1,2})
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# 10X
# 10 X
# ============================================================

PADRAO_NX = re.compile(
    r"""
    \b
    (?P<total>\d{1,2})
    \s*
    X
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# 10X SEM JUROS
# ============================================================

PADRAO_NX_SEM_JUROS = re.compile(
    r"""
    (?P<total>\d{1,2})
    \s*
    X
    \s*
    SEM
    \s*
    JUROS
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# PARCELADO SEM JUROS
# ============================================================

PADRAO_PARCELADO_SEM_JUROS = re.compile(
    r"""
    PARCELADO
    \s*
    SEM
    \s*
    JUROS
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# EM 6X
# EM 10X
# ============================================================

PADRAO_EM_NX = re.compile(
    r"""
    EM
    \s*
    (?P<total>\d{1,2})
    \s*
    X
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# 6 PARCELAS
# 06 PARCELAS
# ============================================================

PADRAO_N_PARCELAS = re.compile(
    r"""
    (?P<total>\d{1,2})
    \s*
    PARCELAS
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# 6 PRESTACOES
# 6 PRESTAÇÕES
# ============================================================

PADRAO_N_PRESTACOES = re.compile(
    r"""
    (?P<total>\d{1,2})
    \s*
    PRESTAC(?:OES|ÕES)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# COMPRA PARCELADA
# ============================================================

PADRAO_COMPRA_PARCELADA = re.compile(
    r"""
    COMPRA
    \s*
    PARCELADA
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ============================================================
# LISTA CENTRAL
# (usar no transaction_engine)
# ============================================================

TODOS_PADROES_PARCELAMENTO = [
    PADRAO_PARCELA_DE,
    PADRAO_PARC_DE,
    PADRAO_PARC_BARRA,
    PADRAO_PARCELA_BARRA,
    PADRAO_BARRA,
    PADRAO_DE,
    PADRAO_NX,
    PADRAO_NX_SEM_JUROS,
    PADRAO_PARCELADO_SEM_JUROS,
    PADRAO_EM_NX,
    PADRAO_N_PARCELAS,
    PADRAO_N_PRESTACOES,
    PADRAO_COMPRA_PARCELADA,
]
