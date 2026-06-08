# ============================================================
# COMPROMISSOS ENGINE
# ORÇAMENTO INTELIGENTE
# Transforma parcelamentos em leitura clara para o cliente
# ============================================================

import pandas as pd


def moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _valor_seguro(linha, coluna, padrao=0):
    try:
        return linha.get(coluna, padrao)
    except Exception:
        return padrao


def analisar_compromissos(df_parcelamentos, gasto_total=0):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return {
            "tem_compromissos": False,
            "qtd_compras": 0,
            "qtd_abertos": 0,
            "qtd_quitados": 0,
            "valor_restante_total": 0,
            "valor_total_compras": 0,
            "impacto_mensal": 0,
            "comprometimento_percentual": 0,
            "maior_compromisso": "-",
            "maior_valor_restante": 0,
            "maior_valor_parcela": 0,
            "maior_parcelas_abertas": 0,
            "nivel_risco": "🟢 Saudável",
            "classificacao": "SAUDÁVEL",
            "mensagem": "Nenhum compromisso parcelado foi identificado.",
            "acao": "Mantenha o pagamento integral da fatura e evite parcelamentos desnecessários.",
            "pode_assumir_novas_parcelas": True
        }

    df = df_parcelamentos.copy()

    for col in ["valor_restante", "valor_total_compra", "valor_parcela", "parcelas_abertas"]:
        if col not in df.columns:
            df[col] = 0

    df["valor_restante"] = pd.to_numeric(df["valor_restante"], errors="coerce").fillna(0)
    df["valor_total_compra"] = pd.to_numeric(df["valor_total_compra"], errors="coerce").fillna(0)
    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0)
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce").fillna(0)

    if "status" in df.columns:
        abertos = df[df["status"] == "ABERTO"].copy()
        quitados = df[df["status"] == "QUITADO"].copy()
    else:
        abertos = df[df["valor_restante"] > 0].copy()
        quitados = df[df["valor_restante"] <= 0].copy()

    valor_restante_total = float(abertos["valor_restante"].sum())
    valor_total_compras = float(df["valor_total_compra"].sum())
    impacto_mensal = float(abertos["valor_parcela"].sum())

    comprometimento_percentual = (
        valor_restante_total / float(gasto_total) * 100
        if gasto_total and float(gasto_total) > 0
        else 0
    )

    if not abertos.empty:
        maior = abertos.sort_values("valor_restante", ascending=False).iloc[0]
        maior_compromisso = str(_valor_seguro(maior, "compra", "-"))
        maior_valor_restante = float(_valor_seguro(maior, "valor_restante", 0))
        maior_valor_parcela = float(_valor_seguro(maior, "valor_parcela", 0))
        maior_parcelas_abertas = int(_valor_seguro(maior, "parcelas_abertas", 0))
    else:
        maior_compromisso = "-"
        maior_valor_restante = 0
        maior_valor_parcela = 0
        maior_parcelas_abertas = 0

    if comprometimento_percentual <= 20:
        nivel_risco = "🟢 Saudável"
        classificacao = "SAUDÁVEL"
        mensagem = (
            f"Você possui {moeda(valor_restante_total)} em parcelas futuras. "
            "O nível de comprometimento está controlado."
        )
        acao = "Evite acumular novas parcelas e mantenha o pagamento integral da fatura."
        pode_assumir = True

    elif comprometimento_percentual <= 40:
        nivel_risco = "🟡 Atenção"
        classificacao = "ATENÇÃO"
        mensagem = (
            f"Você possui {moeda(valor_restante_total)} em parcelas futuras. "
            "O nível de parcelamento exige atenção."
        )
        acao = "Antes de assumir nova parcela, revise os compromissos atuais."
        pode_assumir = False

    elif comprometimento_percentual <= 60:
        nivel_risco = "🟠 Alto"
        classificacao = "ALTO"
        mensagem = (
            f"Você possui {moeda(valor_restante_total)} em parcelas futuras. "
            "Seu comprometimento futuro está alto."
        )
        acao = "Evite novas parcelas e priorize reduzir os compromissos mais pesados."
        pode_assumir = False

    else:
        nivel_risco = "🔴 Crítico"
        classificacao = "CRÍTICO"
        mensagem = (
            f"Você possui {moeda(valor_restante_total)} em parcelas futuras. "
            "O comprometimento futuro está crítico."
        )
        acao = "Não assuma novas parcelas. Priorize quitar ou reduzir os maiores compromissos."
        pode_assumir = False

    return {
        "tem_compromissos": valor_restante_total > 0,
        "qtd_compras": len(df),
        "qtd_abertos": len(abertos),
        "qtd_quitados": len(quitados),
        "valor_restante_total": valor_restante_total,
        "valor_total_compras": valor_total_compras,
        "impacto_mensal": impacto_mensal,
        "comprometimento_percentual": comprometimento_percentual,
        "maior_compromisso": maior_compromisso,
        "maior_valor_restante": maior_valor_restante,
        "maior_valor_parcela": maior_valor_parcela,
        "maior_parcelas_abertas": maior_parcelas_abertas,
        "nivel_risco": nivel_risco,
        "classificacao": classificacao,
        "mensagem": mensagem,
        "acao": acao,
        "pode_assumir_novas_parcelas": pode_assumir
    }


def gerar_resumo_executivo_compromissos(resultado):
    if not resultado.get("tem_compromissos", False):
        return (
            "Nenhuma compra parcelada em aberto foi identificada. "
            "Seu nível de compromissos futuros está saudável."
        )

    return (
        f"Foram identificadas {resultado['qtd_abertos']} compras parceladas em aberto. "
        f"Você ainda possui {moeda(resultado['valor_restante_total'])} para pagar. "
        f"O impacto mensal estimado é de {moeda(resultado['impacto_mensal'])}. "
        f"O maior compromisso é {resultado['maior_compromisso']}, com "
        f"{moeda(resultado['maior_valor_restante'])} restantes. "
        f"Classificação: {resultado['nivel_risco']}. "
        f"{resultado['acao']}"
    )


def gerar_top_compromissos(df_parcelamentos, top=5):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return pd.DataFrame()

    df = df_parcelamentos.copy()

    colunas_necessarias = [
        "compra",
        "valor_parcela",
        "parcelas_abertas",
        "valor_restante",
        "status"
    ]

    for col in colunas_necessarias:
        if col not in df.columns:
            df[col] = 0 if col != "compra" and col != "status" else "-"

    df["valor_restante"] = pd.to_numeric(df["valor_restante"], errors="coerce").fillna(0)
    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0)
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce").fillna(0).astype(int)

    df = df[df["valor_restante"] > 0].copy()

    if df.empty:
        return pd.DataFrame()

    df = df.sort_values("valor_restante", ascending=False).head(top)

    return df[
        [
            "compra",
            "valor_parcela",
            "parcelas_abertas",
            "valor_restante",
            "status"
        ]
    ]


def gerar_texto_capacidade(resultado):
    if resultado.get("classificacao") == "SAUDÁVEL":
        return (
            "Você ainda está em uma zona saudável, mas novas parcelas devem ter objetivo claro. "
            "Evite parcelar consumo recorrente como mercado, combustível e alimentação."
        )

    if resultado.get("classificacao") == "ATENÇÃO":
        return (
            "Você deve evitar novas parcelas neste momento. "
            "O ideal é esperar reduzir parte dos compromissos atuais."
        )

    if resultado.get("classificacao") == "ALTO":
        return (
            "Seu nível de parcelamento está alto. "
            "A prioridade deve ser reduzir os maiores compromissos antes de comprar novamente a prazo."
        )

    return (
        "Seu nível de parcelamento está crítico. "
        "Não é recomendado assumir novas parcelas até reduzir significativamente os compromissos atuais."
    )
