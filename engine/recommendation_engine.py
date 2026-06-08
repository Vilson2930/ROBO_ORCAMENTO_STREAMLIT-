# ============================================================
# RECOMMENDATION ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

def gerar_recomendacoes(resumo_categoria, diagnostico, df_parcelamentos):

    recomendacoes = []

    if resumo_categoria is None or resumo_categoria.empty:
        return [
            {
                "tipo": "SEM_DADOS",
                "titulo": "Dados insuficientes",
                "descricao": "Não foi possível gerar recomendações com os dados atuais."
            }
        ]

    if "valor_total" not in resumo_categoria.columns:
        return [
            {
                "tipo": "ERRO",
                "titulo": "Erro na leitura das categorias",
                "descricao": "O sistema não encontrou a coluna valor_total no resumo de categorias."
            }
        ]

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
                "tipo": "ATENÇÃO",
                "titulo": "Combustível elevado",
                "descricao": f"Combustível representa {percentual:.2f}% dos gastos."
            })

    # --------------------------------------------------------
    # ALIMENTAÇÃO FORA
    # --------------------------------------------------------

    if "Alimentação fora de casa" in resumo_categoria.index:

        percentual = resumo_categoria.loc[
            "Alimentação fora de casa",
            "percentual_total"
        ]

        if percentual > 10:
            recomendacoes.append({
                "tipo": "ATENÇÃO",
                "titulo": "Alimentação fora de casa elevada",
                "descricao": f"Representa {percentual:.2f}% dos gastos."
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
                "tipo": "ATENÇÃO",
                "titulo": "Compras acima do ideal",
                "descricao": f"Representa {percentual:.2f}% dos gastos."
            })

    # --------------------------------------------------------
    # PARCELAMENTOS
    # --------------------------------------------------------

    if df_parcelamentos is not None and not df_parcelamentos.empty:
        if "status" in df_parcelamentos.columns and "valor_restante" in df_parcelamentos.columns:

            abertos = df_parcelamentos[
                df_parcelamentos["status"] == "ABERTO"
            ]

            if len(abertos) > 0:
                maior = abertos.sort_values(
                    "valor_restante",
                    ascending=False
                ).iloc[0]

                recomendacoes.append({
                    "tipo": "PARCELAMENTO",
                    "titulo": "Maior compromisso futuro",
                    "descricao": f"{maior['compra']} - R$ {maior['valor_restante']:,.2f}"
                })

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = diagnostico.get("score", 0)

    if score >= 85:
        recomendacoes.append({
            "tipo": "POSITIVO",
            "titulo": "Boa organização financeira",
            "descricao": "Os indicadores mostram boa gestão dos gastos."
        })

    elif score >= 70:
        recomendacoes.append({
            "tipo": "MODERADO",
            "titulo": "Há espaço para melhorias",
            "descricao": "Pequenos ajustes podem aumentar sua eficiência financeira."
        })

    else:
        recomendacoes.append({
            "tipo": "RISCO",
            "titulo": "Atenção ao orçamento",
            "descricao": "Existem sinais que merecem acompanhamento."
        })

    return recomendacoes


def gerar_plano_acao(recomendacoes):

    if not recomendacoes:
        return "Nenhuma recomendação gerada."

    linhas = []

    for item in recomendacoes:
        linhas.append(
            f"• {item['titulo']} - {item['descricao']}"
        )

    return "\n".join(linhas)
