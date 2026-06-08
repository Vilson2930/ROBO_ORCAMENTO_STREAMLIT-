# ============================================================
# DIAGNOSTICO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão profissional — score coerente com parcelamentos e risco
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
        "score": 0,
        "classificacao": classificacao,
        "nivel_comprometimento": "SEM DADOS",
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
    if percentual <= 20:
        return "SAUDÁVEL"
    if percentual <= 40:
        return "ATENÇÃO"
    if percentual <= 60:
        return "ALTO"
    return "CRÍTICO"


def limitar_score_por_comprometimento(score, percentual):
    """
    Impede inconsistência:
    se o comprometimento futuro é alto, o score não pode continuar excelente.
    """

    if percentual > 60:
        return min(score, 40)

    if percentual > 40:
        return min(score, 60)

    if percentual > 20:
        return min(score, 80)

    return score


def gerar_diagnostico(resumo_categoria, df_parcelamentos):

    if resumo_categoria is None or resumo_categoria.empty:
        return _retorno_vazio("SEM DADOS")

    if "valor_total" not in resumo_categoria.columns:
        return _retorno_vazio("ERRO NA CATEGORIA")

    gasto_total = float(resumo_categoria["valor_total"].sum())

    if gasto_total <= 0:
        return _retorno_vazio("SEM GASTOS")

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

    nivel_comprometimento = classificar_comprometimento(
        comprometimento_percentual
    )

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
    # MAIOR COMPROMISSO
    # ========================================================

    if ativos is not None and len(ativos) > 0:

        maior = ativos.sort_values(
            "valor_restante",
            ascending=False
        ).iloc[0]

        compra_risco = str(maior.get("compra", "-"))

        valor_risco = float(
            maior.get("valor_restante", 0)
        )

        valor_parcela_risco = float(
            maior.get("valor_parcela", 0)
        )

        parcelas_abertas_risco = int(
            maior.get("parcelas_abertas", 0)
        )

    else:
        compra_risco = "-"
        valor_risco = 0
        valor_parcela_risco = 0
        parcelas_abertas_risco = 0

    # ========================================================
    # SCORE FINANCEIRO
    # ========================================================

    score = 100

    # Concentração de gastos
    if percentual_categoria > 40:
        score -= 20
    elif percentual_categoria > 30:
        score -= 15
    elif percentual_categoria > 25:
        score -= 10

    # Comprometimento futuro
    if comprometimento_percentual > 60:
        score -= 45
    elif comprometimento_percentual > 40:
        score -= 30
    elif comprometimento_percentual > 20:
        score -= 15

    # Quantidade de parcelamentos abertos
    qtd_ativos = len(ativos) if ativos is not None else 0

    if qtd_ativos > 10:
        score -= 15
    elif qtd_ativos > 5:
        score -= 10
    elif qtd_ativos > 3:
        score -= 5

    # Maior compromisso individual
    if valor_risco > gasto_total * 0.50:
        score -= 20
    elif valor_risco > gasto_total * 0.30:
        score -= 10

    score = max(score, 0)

    # Regra de coerência institucional
    score = limitar_score_por_comprometimento(
        score,
        comprometimento_percentual
    )

    classificacao = classificar_score(score)

    # ========================================================
    # ALERTA E AÇÃO PRIORITÁRIA
    # ========================================================

    if comprometimento_percentual > 60:
        alerta_principal = (
            "Comprometimento futuro crítico. As parcelas futuras representam "
            f"{comprometimento_percentual:.1f}% dos gastos analisados."
        )
        acao_prioritaria = (
            "Evite novas parcelas e priorize reduzir os compromissos já assumidos."
        )

    elif comprometimento_percentual > 40:
        alerta_principal = (
            "Comprometimento futuro elevado. O volume de parcelas exige atenção."
        )
        acao_prioritaria = (
            "Revise as compras parceladas antes de assumir novas despesas."
        )

    elif percentual_categoria > 30:
        alerta_principal = (
            f"Alta concentração em {nome_categoria}. "
            f"Essa categoria representa {percentual_categoria:.1f}% dos gastos."
        )
        acao_prioritaria = (
            f"Comece reduzindo gastos na categoria {nome_categoria}."
        )

    elif parcelas_futuras > 0:
        alerta_principal = (
            "Existem parcelas futuras, mas o nível ainda parece controlado."
        )
        acao_prioritaria = (
            "Acompanhe os parcelamentos e evite acumular novas compras a prazo."
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
        "score": int(round(score, 0)),
        "classificacao": classificacao,
        "nivel_comprometimento": nivel_comprometimento,
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

Comprometimento futuro: {diagnostico['comprometimento_percentual']:.1f}%
Nível de comprometimento: {diagnostico['nivel_comprometimento']}

Score financeiro: {diagnostico['score']}/100
Classificação: {diagnostico['classificacao']}

Alerta principal:
{diagnostico['alerta_principal']}

Ação prioritária:
{diagnostico['acao_prioritaria']}
"""
