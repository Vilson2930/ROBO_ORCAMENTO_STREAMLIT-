# ============================================================
# DIAGNOSTICO ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

import pandas as pd

# ============================================================
# GERAR DIAGNÓSTICO
# ============================================================

def gerar_diagnostico(
    resumo_categoria,
    df_parcelamentos
):

    diagnostico = {}

    # --------------------------------------------------------
    # GASTO TOTAL
    # --------------------------------------------------------

    gasto_total = float(
        resumo_categoria["valor_total"].sum()
    )

    # --------------------------------------------------------
    # PARCELAS FUTURAS
    # --------------------------------------------------------

    parcelas_futuras = float(
        df_parcelamentos[
            "valor_restante"
        ].sum()
    )

    # --------------------------------------------------------
    # COMPROMISSO TOTAL
    # --------------------------------------------------------

    compromisso_total = (
        gasto_total +
        parcelas_futuras
    )

    # --------------------------------------------------------
    # MAIOR CATEGORIA
    # --------------------------------------------------------

    top_categoria = (
        resumo_categoria
        .sort_values(
            "valor_total",
            ascending=False
        )
        .iloc[0]
    )

    nome_categoria = (
        resumo_categoria
        .sort_values(
            "valor_total",
            ascending=False
        )
        .index[0]
    )

    # --------------------------------------------------------
    # MAIOR PARCELAMENTO
    # --------------------------------------------------------

    ativos = df_parcelamentos[
        df_parcelamentos["status"] == "ABERTO"
    ]

    if len(ativos) > 0:

        maior_parcelamento = (
            ativos
            .sort_values(
                "valor_restante",
                ascending=False
            )
            .iloc[0]
        )

        compra_risco = (
            maior_parcelamento["compra"]
        )

        valor_risco = float(
            maior_parcelamento[
                "valor_restante"
            ]
        )

    else:

        compra_risco = "-"
        valor_risco = 0

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = 100

    if parcelas_futuras > gasto_total * 0.20:
        score -= 20

    if top_categoria[
        "percentual_total"
    ] > 25:
        score -= 10

    if len(ativos) > 10:
        score -= 10

    score = max(score, 0)

    # --------------------------------------------------------
    # CLASSIFICAÇÃO
    # --------------------------------------------------------

    if score >= 85:

        classificacao = "EXCELENTE"

    elif score >= 70:

        classificacao = "BOA"

    elif score >= 50:

        classificacao = "MODERADA"

    else:

        classificacao = "ATENCAO"

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    diagnostico = {

        "gasto_total":
            gasto_total,

        "parcelas_futuras":
            parcelas_futuras,

        "compromisso_total":
            compromisso_total,

        "categoria_principal":
            nome_categoria,

        "valor_categoria_principal":
            float(
                top_categoria[
                    "valor_total"
                ]
            ),

        "compra_risco":
            compra_risco,

        "valor_risco":
            valor_risco,

        "score":
            score,

        "classificacao":
            classificacao

    }

    return diagnostico


# ============================================================
# RELATÓRIO SIMPLES
# ============================================================

def gerar_relatorio_simples(
    diagnostico
):

    linhas = []

    linhas.append(
        f"Gasto total: R$ {diagnostico['gasto_total']:,.2f}"
    )

    linhas.append(
        f"Parcelas futuras: R$ {diagnostico['parcelas_futuras']:,.2f}"
    )

    linhas.append(
        f"Compromisso total: R$ {diagnostico['compromisso_total']:,.2f}"
    )

    linhas.append(
        f"Maior categoria: {diagnostico['categoria_principal']}"
    )

    linhas.append(
        f"Maior parcelamento: {diagnostico['compra_risco']}"
    )

    linhas.append(
        f"Score financeiro: {diagnostico['score']}"
    )

    linhas.append(
        f"Classificação: {diagnostico['classificacao']}"
    )

    return "\n".join(linhas)
