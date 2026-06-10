# ============================================================
# confidence.py
# ORÇAMENTO INTELIGENTE
# Confidence Engine Institucional
# Versão 2.0
# ============================================================

from datetime import datetime


CONFIDENCE_VERSION = "2.0"


# ============================================================
# NÍVEL
# ============================================================

def _nivel(score):

    if score >= 98:
        return "EXCELENTE"

    if score >= 90:
        return "ALTA"

    if score >= 75:
        return "BOA"

    if score >= 60:
        return "MEDIA"

    return "BAIXA"


# ============================================================
# ENGINE
# ============================================================

def calcular_confianca(
    linha_original="",
    descricao="",
    valor=None,
    data=None,
    parcela_atual=None,
    parcela_total=None,
    merchant=None,
):

    score = 100

    motivos = []

    evidencias = []

    # --------------------------------------------------------
    # linha original
    # --------------------------------------------------------

    linha_original = str(linha_original or "").strip()

    if linha_original:

        evidencias.append("linha_original")

    else:

        score -= 15
        motivos.append("SEM_LINHA_ORIGINAL")

    # --------------------------------------------------------
    # descricao
    # --------------------------------------------------------

    descricao = str(descricao or "").strip()

    if descricao:

        evidencias.append("descricao")

    else:

        score -= 20
        motivos.append("SEM_DESCRICAO")

    if len(descricao) > 120:

        score -= 5
        motivos.append("DESCRICAO_MUITO_LONGA")

    # --------------------------------------------------------
    # merchant
    # --------------------------------------------------------

    merchant = str(merchant or "").strip()

    if merchant:

        evidencias.append("merchant")

    # --------------------------------------------------------
    # valor
    # --------------------------------------------------------

    try:

        valor = float(valor)

        if valor > 0:

            evidencias.append("valor")

        else:

            score -= 30
            motivos.append("VALOR_INVALIDO")

    except Exception:

        score -= 30
        motivos.append("VALOR_INVALIDO")

    # --------------------------------------------------------
    # data
    # --------------------------------------------------------

    if data not in [None, ""]:

        evidencias.append("data")

    else:

        score -= 15
        motivos.append("SEM_DATA")

    # --------------------------------------------------------
    # parcela
    # --------------------------------------------------------

    if parcela_atual is not None and parcela_total is not None:

        try:

            pa = int(parcela_atual)
            pt = int(parcela_total)

            if pa >= 1:

                evidencias.append("parcela_atual")

            else:

                score -= 10
                motivos.append("PARCELA_ATUAL_INVALIDA")

            if pt >= 1:

                evidencias.append("parcela_total")

            else:

                score -= 10
                motivos.append("PARCELA_TOTAL_INVALIDA")

            if pa > pt:

                score -= 20
                motivos.append("PARCELA_MAIOR_QUE_TOTAL")

        except Exception:

            score -= 15
            motivos.append("ERRO_PARCELAMENTO")

    # --------------------------------------------------------
    # caracteres estranhos
    # --------------------------------------------------------

    especiais = 0

    for c in linha_original:

        if c in "@#$%¨&{}[]<>":

            especiais += 1

    if especiais >= 5:

        score -= 5
        motivos.append("RUIDO_CARACTERES")

    # --------------------------------------------------------
    # limpeza
    # --------------------------------------------------------

    score = max(0, min(100, int(score)))

    # --------------------------------------------------------
    # retorno institucional
    # --------------------------------------------------------

    return {

        "confidence_version": CONFIDENCE_VERSION,

        "confidence_raw": score,

        "confidence_final": score,

        "confidence_level": _nivel(score),

        "confianca_extracao": score,

        "evidencias": len(evidencias),

        "lista_evidencias": evidencias,

        "motivos": motivos,

        "timestamp": datetime.now().isoformat(),

    }


# ============================================================
# WRAPPER
# ============================================================

def score_extracao(**kwargs):

    return calcular_confianca(**kwargs)
