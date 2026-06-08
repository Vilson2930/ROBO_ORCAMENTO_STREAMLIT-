# ============================================================
# DIAGNOSTICO ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

def gerar_diagnostico(resumo_categoria, df_parcelamentos):

    if resumo_categoria is None or resumo_categoria.empty:
        return {
            "gasto_total": 0,
            "parcelas_futuras": 0,
            "compromisso_total": 0,
            "categoria_principal": "-",
            "valor_categoria_principal": 0,
            "compra_risco": "-",
            "valor_risco": 0,
            "score": 0,
            "classificacao": "SEM DADOS"
        }

    if "valor_total" not in resumo_categoria.columns:
        return {
            "gasto_total": 0,
            "parcelas_futuras": 0,
            "compromisso_total": 0,
            "categoria_principal": "-",
            "valor_categoria_principal": 0,
            "compra_risco": "-",
            "valor_risco": 0,
            "score": 0,
            "classificacao": "ERRO NA CATEGORIA"
        }

    gasto_total = float(resumo_categoria["valor_total"].sum())

    if df_parcelamentos is None or df_parcelamentos.empty:
        parcelas_futuras = 0
        ativos = df_parcelamentos
    else:
        parcelas_futuras = float(df_parcelamentos["valor_restante"].sum())
        ativos = df_parcelamentos[df_parcelamentos["status"] == "ABERTO"]

    compromisso_total = gasto_total + parcelas_futuras

    resumo_ordenado = resumo_categoria.sort_values(
        "valor_total",
        ascending=False
    )

    nome_categoria = resumo_ordenado.index[0]
    valor_categoria = float(resumo_ordenado.iloc[0]["valor_total"])
    percentual_categoria = float(resumo_ordenado.iloc[0].get("percentual_total", 0))

    if ativos is not None and len(ativos) > 0:
        maior = ativos.sort_values("valor_restante", ascending=False).iloc[0]
        compra_risco = maior["compra"]
        valor_risco = float(maior["valor_restante"])
    else:
        compra_risco = "-"
        valor_risco = 0

    score = 100

    if parcelas_futuras > gasto_total * 0.20:
        score -= 20

    if percentual_categoria > 25:
        score -= 10

    if ativos is not None and len(ativos) > 10:
        score -= 10

    score = max(score, 0)

    if score >= 85:
        classificacao = "EXCELENTE"
    elif score >= 70:
        classificacao = "BOA"
    elif score >= 50:
        classificacao = "MODERADA"
    else:
        classificacao = "ATENÇÃO"

    return {
        "gasto_total": gasto_total,
        "parcelas_futuras": parcelas_futuras,
        "compromisso_total": compromisso_total,
        "categoria_principal": nome_categoria,
        "valor_categoria_principal": valor_categoria,
        "compra_risco": compra_risco,
        "valor_risco": valor_risco,
        "score": score,
        "classificacao": classificacao
    }


def gerar_relatorio_simples(diagnostico):

    return f"""
Gasto total: R$ {diagnostico['gasto_total']:,.2f}
Parcelas futuras: R$ {diagnostico['parcelas_futuras']:,.2f}
Compromisso total: R$ {diagnostico['compromisso_total']:,.2f}

Maior categoria: {diagnostico['categoria_principal']}
Maior parcelamento: {diagnostico['compra_risco']}

Score financeiro: {diagnostico['score']}/100
Classificação: {diagnostico['classificacao']}
"""
