# ============================================================
# parcel_patterns.py
# ORÇAMENTO INTELIGENTE
# Biblioteca Nacional de Parcelamentos
# Versão corrigida — padrões seguros
# ============================================================

import re


PADRAO_PARCELA_DE = re.compile(
    r"\bPARCELA\s*(?P<atual>\d{1,2})\s*DE\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)

PADRAO_PARC_DE = re.compile(
    r"\bPARC\.?\s*(?P<atual>\d{1,2})\s*DE\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)

PADRAO_PARC_BARRA = re.compile(
    r"\bPARC\.?\s*(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)

PADRAO_PARCELA_BARRA = re.compile(
    r"\bPARCELA\s*(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)

PADRAO_NX_SEM_JUROS = re.compile(
    r"\b(?P<total>\d{1,2})\s*X\s*SEM\s*JUROS\b",
    re.IGNORECASE,
)

PADRAO_EM_NX = re.compile(
    r"\bEM\s*(?P<total>\d{1,2})\s*X\b",
    re.IGNORECASE,
)

PADRAO_NX = re.compile(
    r"\b(?P<total>\d{1,2})\s*X\b",
    re.IGNORECASE,
)

PADRAO_N_PARCELAS = re.compile(
    r"\b(?P<total>\d{1,2})\s*PARCELAS\b",
    re.IGNORECASE,
)

PADRAO_N_PRESTACOES = re.compile(
    r"\b(?P<total>\d{1,2})\s*PRESTAC(?:OES|ÕES)\b",
    re.IGNORECASE,
)

PADRAO_COMPRA_PARCELADA = re.compile(
    r"\bCOMPRA\s*PARCELADA\b",
    re.IGNORECASE,
)

PADRAO_PARCELADO_SEM_JUROS = re.compile(
    r"\bPARCELADO\s*SEM\s*JUROS\b",
    re.IGNORECASE,
)


# ============================================================
# PADRÕES PERIGOSOS
# Só use com contexto explícito no código chamador.
# Não colocar na lista central.
# ============================================================

PADRAO_BARRA_CONTEXTUAL = re.compile(
    r"\b(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)

PADRAO_DE_CONTEXTUAL = re.compile(
    r"\b(?P<atual>\d{1,2})\s*DE\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)


# ============================================================
# LISTA CENTRAL SEGURA
# ============================================================

TODOS_PADROES_PARCELAMENTO = [
    PADRAO_PARCELA_DE,
    PADRAO_PARC_DE,
    PADRAO_PARC_BARRA,
    PADRAO_PARCELA_BARRA,
    PADRAO_NX_SEM_JUROS,
    PADRAO_EM_NX,
    PADRAO_NX,
    PADRAO_N_PARCELAS,
    PADRAO_N_PRESTACOES,
    PADRAO_COMPRA_PARCELADA,
    PADRAO_PARCELADO_SEM_JUROS,
]
