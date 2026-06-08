# ============================================================
# RECOMMENDATION ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

# ============================================================
# GERAR RECOMENDAÇÕES
# ============================================================

def gerar_recomendacoes(
    resumo_categoria,
    diagnostico,
    df_parcelamentos
):

    recomendacoes = []

    # --------------------------------------------------------
    # TOP CATEGORIAS
    # --------------------------------------------------------

    top_categorias = (
        resumo_categoria
        .sort_values(
            "valor_total",
            ascending=False
        )
        .head(5)
    )

    # --------------------------------------------------------
    # COMBUSTÍVEL
    # --------------------------------------------------------

    if "Combustível" in resumo_categoria.index:

        percentual = resumo_categoria.loc[
            "Combustível",
            "percentual_total"
        ]

        if percentual > 20:

            recomendacoes.append({

                "tipo": "ATENCAO",

                "titulo":
                    "Combustível elevado",

                "descricao":
                    f"Combustível representa "
                    f"{percentual:.2f}% "
                    f"dos gastos."

            })

    # --------------------------------------------------------
    # ALIMENTAÇÃO
    # --------------------------------------------------------

    if "Alimentação fora de casa" in resumo_categoria.index:

        percentual = resumo_categoria.loc[
            "Alimentação fora de casa",
            "percentual_total"
        ]

        if percentual > 10:

            recomendacoes.append({

                "tipo": "ATENCAO",

                "titulo":
                    "Alimentação fora de casa",

                "descricao":
                    f"Representa "
                    f"{percentual:.2f}% "
                    f"dos gastos."

            })

    # --------------------------------------------------------
    # COMPRAS
    # --------------------------------------------------------

    if "Vestuário / Compras" in resumo_categoria.index:

        percentual = resumo_categoria.loc[
            "Vestuário / Compras",
            "percentual_total"
        ]

        if percentual > 10:

            recomendacoes.append({

                "tipo": "ATENCAO",

                "titulo":
                    "Compras acima do ideal",

                "descricao":
                    f"Representa "
                    f"{percentual:.2f}% "
                    f"dos gastos."

            })

    # --------------------------------------------------------
    # PARCELAMENTOS
    # --------------------------------------------------------

    abertos = df_parcelamentos[
        df_parcelamentos["status"]
        == "ABERTO"
    ]

    if len(abertos) > 0:

        maior = (
            abertos
            .sort_values(
                "valor_restante",
                ascending=False
            )
            .iloc[0]
        )

        recomendacoes.append({

            "tipo": "PARCELAMENTO",

            "titulo":
                "Maior compromisso futuro",

            "descricao":
                f"{maior['compra']} "
                f"(R$ {maior['valor_restante']:,.2f})"

        })

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = diagnostico["score"]

    if score >= 85:

        recomendacoes.append({

            "tipo": "POSITIVO",

            "titulo":
                "Boa organização financeira",

            "descricao":
                "Os indicadores mostram "
                "boa gestão dos gastos."

        })

    elif score >= 70:

        recomendacoes.append({

            "tipo": "MODERADO",

            "titulo":
                "Há espaço para melhorias",

            "descricao":
                "Pequenos ajustes podem "
                "aumentar sua eficiência."

        })

    else:

        recomendacoes.append({

            "tipo": "RISCO",

            "titulo":
                "Atenção ao orçamento",

            "descricao":
                "Existem sinais que merecem "
                "acompanhamento."

        })

    return recomendacoes


# ============================================================
# RELATÓRIO EXECUTIVO
# ============================================================

def gerar_plano_acao(
    recomendacoes
):

    plano = []

    for item in recomendacoes:

        plano.append(

            f"• {item['titulo']} - "
            f"{item['descricao']}"

        )

    return "\n".join(plano)
