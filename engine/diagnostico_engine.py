# ============================================================
# DIAGNOSTICO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão 2.0 — separa gasto, parcelamento e risco mensal
# ============================================================


def _retorno_vazio(classificacao="SEM DADOS"):
    return {
        "gasto_total": 0,
        "parcelas_futuras": 0,
        "compromisso_total": 0,

        "categoria_principal": "-",
        "valor_categoria_principal": 0,
        "percentual_categoria_principal": 0,

        "compra_risco": "-",
        "valor_risco": 0,
        "valor_parcela_risco": 0,
        "parcelas_abertas_risco": 0,

        "comprometimento_percentual": 0,
        "impacto_mensal": 0,
        "impacto_mensal_percentual": 0,

        "score": 0,
        "classificacao": classificacao,
        "nivel_comprometimento": "SEM DADOS",
        "nivel_impacto_mensal": "SEM DADOS",

        "score_gastos": 0,
        "score_parcelas": 0,
        "score_geral": 0,

        "alerta_principal": "Nenhum dado financeiro disponível.",
        "acao_prioritaria": "Envie uma fatura para gerar o diagnóstico."
    }


def classificar_score(score):
    if score >= 85:
        return "EXCELENTE"
    if score >= 70:
        return "BOA"
    if score >= 50:
        return "MODERADA"
    if score >= 30:
        return "ATENÇÃO"
    return "CRÍTICA"


def classificar_comprometimento(percentual):
    if percentual <= 30:
        return "SAUDÁVEL"
    if percentual <= 80:
        return "ATENÇÃO"
    if percentual <= 150:
        return "ALTO"
    return "CRÍTICO"


def classificar_impacto_mensal(percentual):
    if percentual <= 10:
        return "SAUDÁVEL"
    if percentual <= 20:
        return "ATENÇÃO"
    if percentual <= 30:
        return "ALTO"
    return "CRÍTICO"


def limitar_score_por_risco(score, impacto_mensal_percentual, comprometimento_percentual):
    """
    Regra de coerência:
    - impacto mensal manda mais que estoque futuro;
    - estoque futuro muito alto impede score excelente, mas não derruba sozinho para crítico.
    """

    if impacto_mensal_percentual > 30:
        score = min(score, 35)
    elif impacto_mensal_percentual > 20:
        score = min(score, 55)
    elif impacto_mensal_percentual > 10:
        score = min(score, 75)

    if comprometimento_percentual > 150:
        score = min(score, 55)
    elif comprometimento_percentual > 80:
        score = min(score, 70)

    return score


def gerar_diagnostico(resumo_categoria, df_parcelamentos, resultado_compromissos=None):

    if resumo_categoria is None or resumo_categoria.empty:
        return _retorno_vazio("SEM DADOS")

    if "valor_total" not in resumo_categoria.columns:
        return _retorno_vazio("ERRO NA CATEGORIA")

    gasto_total = float(resumo_categoria["valor_total"].sum())

    if gasto_total <= 0:
        return _retorno_vazio("SEM GASTOS")

    # ========================================================
    # CATEGORIA PRINCIPAL
    # ========================================================

    resumo_ordenado = resumo_categoria.sort_values(
        "valor_total",
        ascending=False
    )

    nome_categoria = resumo_ordenado.index[0]
    valor_categoria = float(resumo_ordenado.iloc[0]["valor_total"])

    percentual_categoria = (
        valor_categoria / gasto_total * 100
        if gasto_total > 0
        else 0
    )

    # ========================================================
    # PARCELAMENTOS
    # ========================================================

    if df_parcelamentos is None or df_parcelamentos.empty:
        parcelas_futuras = 0
        ativos = None
    else:
        df_parcelamentos = df_parcelamentos.copy()

        if "valor_restante" in df_parcelamentos.columns:
            parcelas_futuras = float(df_parcelamentos["valor_restante"].sum())
        else:
            parcelas_futuras = 0

        if "status" in df_parcelamentos.columns:
            ativos = df_parcelamentos[df_parcelamentos["status"] == "ABERTO"]
        else:
            ativos = df_parcelamentos

    compromisso_total = gasto_total + parcelas_futuras

    comprometimento_percentual = (
        parcelas_futuras / gasto_total * 100
        if gasto_total > 0
        else 0
    )

    impacto_mensal = 0
    impacto_mensal_percentual = 0

    if resultado_compromissos:
        impacto_mensal = float(resultado_compromissos.get("impacto_mensal", 0))
        impacto_mensal_percentual = float(
            resultado_compromissos.get("impacto_mensal_percentual", 0)
        )
        parcelas_futuras = float(
            resultado_compromissos.get("valor_restante_total", parcelas_futuras)
        )
        comprometimento_percentual = float(
            resultado_compromissos.get("comprometimento_percentual", comprometimento_percentual)
        )

    elif ativos is not None and len(ativos) > 0 and "valor_parcela" in ativos.columns:
        impacto_mensal = float(ativos["valor_parcela"].sum())
        impacto_mensal_percentual = (
            impacto_mensal / gasto_total * 100
            if gasto_total > 0
            else 0
        )

    nivel_comprometimento = classificar_comprometimento(
        comprometimento_percentual
    )

    nivel_impacto_mensal = classificar_impacto_mensal(
        impacto_mensal_percentual
    )

    # ========================================================
    # MAIOR COMPROMISSO
    # ========================================================

    if ativos is not None and len(ativos) > 0:

        maior = ativos.sort_values(
            "valor_restante",
            ascending=False
        ).iloc[0]

        compra_risco = str(maior.get("compra", "-"))
        valor_risco = float(maior.get("valor_restante", 0))
        valor_parcela_risco = float(maior.get("valor_parcela", 0))
        parcelas_abertas_risco = int(maior.get("parcelas_abertas", 0))

    else:
        compra_risco = "-"
        valor_risco = 0
        valor_parcela_risco = 0
        parcelas_abertas_risco = 0

    # ========================================================
    # SCORE DE GASTOS
    # ========================================================

    score_gastos = 100

    if percentual_categoria > 45:
        score_gastos -= 30
    elif percentual_categoria > 35:
        score_gastos -= 20
    elif percentual_categoria > 25:
        score_gastos -= 10

    score_gastos = max(score_gastos, 0)

    # ========================================================
    # SCORE DE PARCELAS
    # ========================================================

    score_parcelas = 100

    if impacto_mensal_percentual > 30:
        score_parcelas -= 60
    elif impacto_mensal_percentual > 20:
        score_parcelas -= 40
    elif impacto_mensal_percentual > 10:
        score_parcelas -= 25

    if comprometimento_percentual > 150:
        score_parcelas -= 20
    elif comprometimento_percentual > 80:
        score_parcelas -= 15
    elif comprometimento_percentual > 30:
        score_parcelas -= 5

    qtd_ativos = len(ativos) if ativos is not None else 0

    if qtd_ativos > 10:
        score_parcelas -= 15
    elif qtd_ativos > 5:
        score_parcelas -= 10
    elif qtd_ativos > 3:
        score_parcelas -= 5

    if valor_parcela_risco > gasto_total * 0.15:
        score_parcelas -= 15
    elif valor_parcela_risco > gasto_total * 0.10:
        score_parcelas -= 10

    score_parcelas = max(score_parcelas, 0)

    # ========================================================
    # SCORE GERAL
    # Peso maior para impacto mensal e controle de parcelas
    # ========================================================

    score_geral = (
        score_gastos * 0.40 +
        score_parcelas * 0.60
    )

    score_geral = limitar_score_por_risco(
        score_geral,
        impacto_mensal_percentual,
        comprometimento_percentual
    )

    score_geral = max(min(score_geral, 100), 0)

    classificacao = classificar_score(score_geral)

    # ========================================================
    # ALERTA E AÇÃO PRIORITÁRIA
    # ========================================================

    if impacto_mensal_percentual > 30:
        alerta_principal = (
            "Impacto mensal crítico. As parcelas consomem "
            f"{impacto_mensal_percentual:.1f}% da referência analisada."
        )
        acao_prioritaria = (
            "Não assuma novas parcelas. Reduza primeiro o valor mensal comprometido."
        )

    elif impacto_mensal_percentual > 20:
        alerta_principal = (
            "Impacto mensal alto. As parcelas já pressionam o orçamento mensal."
        )
        acao_prioritaria = (
            "Priorize quitar ou antecipar as parcelas de maior impacto mensal."
        )

    elif impacto_mensal_percentual > 10:
        alerta_principal = (
            "Parcelamentos em nível de atenção. O impacto mensal ainda não é crítico, "
            "mas já exige controle."
        )
        acao_prioritaria = (
            "Evite novas parcelas até reduzir parte dos compromissos atuais."
        )

    elif comprometimento_percentual > 150:
        alerta_principal = (
            "Estoque futuro de parcelas muito elevado. O peso mensal está controlado, "
            "mas o volume total de compromissos exige acompanhamento."
        )
        acao_prioritaria = (
            "Acompanhe o calendário de parcelas e evite alongar novas compras."
        )

    elif percentual_categoria > 35:
        alerta_principal = (
            f"Alta concentração em {nome_categoria}. "
            f"Essa categoria representa {percentual_categoria:.1f}% dos gastos."
        )
        acao_prioritaria = (
            f"Comece reduzindo gastos na categoria {nome_categoria}."
        )

    elif parcelas_futuras > 0:
        alerta_principal = (
            "Existem parcelas futuras, mas o impacto mensal está controlado."
        )
        acao_prioritaria = (
            "Mantenha o pagamento integral da fatura e evite acumular novas compras a prazo."
        )

    else:
        alerta_principal = (
            "Nenhum risco financeiro relevante foi identificado."
        )
        acao_prioritaria = (
            "Mantenha o controle dos gastos e acompanhe a evolução mensal."
        )

    return {
        "gasto_total": gasto_total,
        "parcelas_futuras": parcelas_futuras,
        "compromisso_total": compromisso_total,

        "categoria_principal": nome_categoria,
        "valor_categoria_principal": valor_categoria,
        "percentual_categoria_principal": percentual_categoria,

        "compra_risco": compra_risco,
        "valor_risco": valor_risco,
        "valor_parcela_risco": valor_parcela_risco,
        "parcelas_abertas_risco": parcelas_abertas_risco,

        "comprometimento_percentual": comprometimento_percentual,
        "impacto_mensal": impacto_mensal,
        "impacto_mensal_percentual": impacto_mensal_percentual,

        "score": int(round(score_geral, 0)),
        "classificacao": classificacao,
        "nivel_comprometimento": nivel_comprometimento,
        "nivel_impacto_mensal": nivel_impacto_mensal,

        "score_gastos": int(round(score_gastos, 0)),
        "score_parcelas": int(round(score_parcelas, 0)),
        "score_geral": int(round(score_geral, 0)),

        "alerta_principal": alerta_principal,
        "acao_prioritaria": acao_prioritaria
    }


def gerar_relatorio_simples(diagnostico):

    return f"""
Gasto total: R$ {diagnostico['gasto_total']:,.2f}
Parcelas futuras: R$ {diagnostico['parcelas_futuras']:,.2f}
Compromisso total: R$ {diagnostico['compromisso_total']:,.2f}

Maior categoria: {diagnostico['categoria_principal']}
Valor da maior categoria: R$ {diagnostico['valor_categoria_principal']:,.2f}
Participação da maior categoria: {diagnostico['percentual_categoria_principal']:.1f}%

Maior compromisso: {diagnostico['compra_risco']}
Valor restante do maior compromisso: R$ {diagnostico['valor_risco']:,.2f}
Parcela mensal do maior compromisso: R$ {diagnostico['valor_parcela_risco']:,.2f}
Parcelas em aberto: {diagnostico['parcelas_abertas_risco']}

Comprometimento futuro total: {diagnostico['comprometimento_percentual']:.1f}%
Impacto mensal das parcelas: R$ {diagnostico['impacto_mensal']:,.2f}
Peso mensal das parcelas: {diagnostico['impacto_mensal_percentual']:.1f}%

Nível de comprometimento futuro: {diagnostico['nivel_comprometimento']}
Nível de impacto mensal: {diagnostico['nivel_impacto_mensal']}

Score de gastos: {diagnostico['score_gastos']}/100
Score de parcelas: {diagnostico['score_parcelas']}/100
Score geral: {diagnostico['score_geral']}/100

Classificação geral: {diagnostico['classificacao']}

Alerta principal:
{diagnostico['alerta_principal']}

Ação prioritária:
{diagnostico['acao_prioritaria']}
"""
