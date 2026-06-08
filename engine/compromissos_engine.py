# ============================================================
# COMPROMISSOS ENGINE
# ORÇAMENTO INTELIGENTE
# Versão 2.0 — foco em impacto mensal, estoque futuro e capacidade
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


def _df_vazio():
    return {
        "tem_compromissos": False,
        "qtd_compras": 0,
        "qtd_abertos": 0,
        "qtd_quitados": 0,

        "valor_restante_total": 0,
        "valor_total_compras": 0,
        "impacto_mensal": 0,
        "impacto_mensal_percentual": 0,

        "comprometimento_percentual": 0,

        "maior_compromisso": "-",
        "maior_valor_restante": 0,
        "maior_valor_parcela": 0,
        "maior_parcelas_abertas": 0,

        "maior_parcela_compra": "-",
        "maior_parcela_valor": 0,
        "maior_parcela_restantes": 0,

        "meses_estimados_comprometidos": 0,

        "nivel_risco": "🟢 Saudável",
        "classificacao": "SAUDÁVEL",
        "mensagem": "Nenhum compromisso parcelado foi identificado.",
        "acao": "Mantenha o pagamento integral da fatura e evite parcelamentos desnecessários.",
        "pode_assumir_novas_parcelas": True
    }


def analisar_compromissos(df_parcelamentos, gasto_total=0, renda_mensal=None):
    """
    Analisa compromissos parcelados.

    gasto_total:
        Total da fatura ou período analisado.

    renda_mensal:
        Opcional. Se informado, calcula quanto das parcelas consome da renda.
        Se não informado, usa gasto_total como referência aproximada.
    """

    if df_parcelamentos is None or df_parcelamentos.empty:
        return _df_vazio()

    df = df_parcelamentos.copy()

    for col in [
        "valor_restante",
        "valor_total_compra",
        "valor_parcela",
        "parcelas_abertas",
        "status",
        "compra"
    ]:
        if col not in df.columns:
            if col in ["status", "compra"]:
                df[col] = "-"
            else:
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

    abertos = abertos[abertos["valor_restante"] > 0].copy()

    if abertos.empty:
        resultado = _df_vazio()
        resultado["qtd_compras"] = len(df)
        resultado["qtd_quitados"] = len(quitados)
        return resultado

    valor_restante_total = float(abertos["valor_restante"].sum())
    valor_total_compras = float(df["valor_total_compra"].sum())

    # Indicador mais importante: quanto pesa no mês
    impacto_mensal = float(abertos["valor_parcela"].sum())

    base_referencia = renda_mensal if renda_mensal else gasto_total

    impacto_mensal_percentual = (
        impacto_mensal / float(base_referencia) * 100
        if base_referencia and float(base_referencia) > 0
        else 0
    )

    # Estoque futuro comparado ao gasto analisado
    comprometimento_percentual = (
        valor_restante_total / float(gasto_total) * 100
        if gasto_total and float(gasto_total) > 0
        else 0
    )

    # Maior saldo restante
    maior_saldo = abertos.sort_values("valor_restante", ascending=False).iloc[0]
    maior_compromisso = str(_valor_seguro(maior_saldo, "compra", "-"))
    maior_valor_restante = float(_valor_seguro(maior_saldo, "valor_restante", 0))
    maior_valor_parcela = float(_valor_seguro(maior_saldo, "valor_parcela", 0))
    maior_parcelas_abertas = int(_valor_seguro(maior_saldo, "parcelas_abertas", 0))

    # Maior parcela mensal
    maior_parcela = abertos.sort_values("valor_parcela", ascending=False).iloc[0]
    maior_parcela_compra = str(_valor_seguro(maior_parcela, "compra", "-"))
    maior_parcela_valor = float(_valor_seguro(maior_parcela, "valor_parcela", 0))
    maior_parcela_restantes = int(_valor_seguro(maior_parcela, "parcelas_abertas", 0))

    meses_estimados_comprometidos = int(abertos["parcelas_abertas"].max())

    # ========================================================
    # CLASSIFICAÇÃO PROFISSIONAL
    # Prioriza impacto mensal, não apenas estoque de dívida
    # ========================================================

    if impacto_mensal_percentual <= 10 and comprometimento_percentual <= 30:
        nivel_risco = "🟢 Saudável"
        classificacao = "SAUDÁVEL"
        pode_assumir = True
        mensagem = (
            f"Você possui {moeda(valor_restante_total)} em parcelas futuras. "
            f"O impacto mensal estimado é de {moeda(impacto_mensal)}, equivalente a "
            f"{impacto_mensal_percentual:.1f}% da referência analisada."
        )
        acao = (
            "Seu nível de parcelas está controlado. Mesmo assim, evite parcelar consumo recorrente."
        )

    elif impacto_mensal_percentual <= 20 and comprometimento_percentual <= 60:
        nivel_risco = "🟡 Atenção"
        classificacao = "ATENÇÃO"
        pode_assumir = False
        mensagem = (
            f"Você possui {moeda(valor_restante_total)} em parcelas futuras. "
            f"As parcelas atuais pesam aproximadamente {moeda(impacto_mensal)} por mês."
        )
        acao = (
            "Evite novas parcelas até reduzir parte dos compromissos atuais."
        )

    elif impacto_mensal_percentual <= 30:
        nivel_risco = "🟠 Alto"
        classificacao = "ALTO"
        pode_assumir = False
        mensagem = (
            f"Você possui {moeda(valor_restante_total)} em parcelas futuras. "
            f"O impacto mensal de {moeda(impacto_mensal)} já pressiona o orçamento."
        )
        acao = (
            "Priorize reduzir os maiores compromissos antes de assumir qualquer nova compra parcelada."
        )

    else:
        nivel_risco = "🔴 Crítico"
        classificacao = "CRÍTICO"
        pode_assumir = False
        mensagem = (
            f"Você possui {moeda(valor_restante_total)} em parcelas futuras. "
            f"O impacto mensal estimado é de {moeda(impacto_mensal)}, acima do nível recomendado."
        )
        acao = (
            "Não assuma novas parcelas. A prioridade é reduzir o impacto mensal antes de novas obrigações."
        )

    return {
        "tem_compromissos": valor_restante_total > 0,
        "qtd_compras": len(df),
        "qtd_abertos": len(abertos),
        "qtd_quitados": len(quitados),

        "valor_restante_total": valor_restante_total,
        "valor_total_compras": valor_total_compras,
        "impacto_mensal": impacto_mensal,
        "impacto_mensal_percentual": impacto_mensal_percentual,

        "comprometimento_percentual": comprometimento_percentual,

        "maior_compromisso": maior_compromisso,
        "maior_valor_restante": maior_valor_restante,
        "maior_valor_parcela": maior_valor_parcela,
        "maior_parcelas_abertas": maior_parcelas_abertas,

        "maior_parcela_compra": maior_parcela_compra,
        "maior_parcela_valor": maior_parcela_valor,
        "maior_parcela_restantes": maior_parcela_restantes,

        "meses_estimados_comprometidos": meses_estimados_comprometidos,

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
        f"Você ainda possui {moeda(resultado['valor_restante_total'])} para pagar no futuro. "
        f"O impacto mensal estimado é de {moeda(resultado['impacto_mensal'])}, "
        f"equivalente a {resultado['impacto_mensal_percentual']:.1f}% da referência analisada. "
        f"A maior parcela mensal é {resultado['maior_parcela_compra']} "
        f"({moeda(resultado['maior_parcela_valor'])}/mês). "
        f"O maior saldo restante é {resultado['maior_compromisso']} "
        f"({moeda(resultado['maior_valor_restante'])}). "
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
        "valor_total_compra",
        "status"
    ]

    for col in colunas_necessarias:
        if col not in df.columns:
            df[col] = 0 if col not in ["compra", "status"] else "-"

    df["valor_restante"] = pd.to_numeric(df["valor_restante"], errors="coerce").fillna(0)
    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0)
    df["valor_total_compra"] = pd.to_numeric(df["valor_total_compra"], errors="coerce").fillna(0)
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
            "valor_total_compra",
            "status"
        ]
    ]


def gerar_top_impacto_mensal(df_parcelamentos, top=5):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return pd.DataFrame()

    df = df_parcelamentos.copy()

    for col in ["compra", "valor_parcela", "parcelas_abertas", "valor_restante", "status"]:
        if col not in df.columns:
            df[col] = 0 if col not in ["compra", "status"] else "-"

    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0)
    df["valor_restante"] = pd.to_numeric(df["valor_restante"], errors="coerce").fillna(0)
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce").fillna(0).astype(int)

    df = df[df["valor_restante"] > 0].copy()

    if df.empty:
        return pd.DataFrame()

    df = df.sort_values("valor_parcela", ascending=False).head(top)

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
            f"O impacto mensal das parcelas é de {moeda(resultado.get('impacto_mensal', 0))}. "
            "Você está em zona saudável, mas novas parcelas devem ter objetivo claro. "
            "Evite parcelar consumo recorrente como mercado, combustível e alimentação."
        )

    if resultado.get("classificacao") == "ATENÇÃO":
        return (
            f"O impacto mensal das parcelas é de {moeda(resultado.get('impacto_mensal', 0))}. "
            "Você deve evitar novas parcelas neste momento. "
            "O ideal é esperar reduzir parte dos compromissos atuais."
        )

    if resultado.get("classificacao") == "ALTO":
        return (
            f"O impacto mensal das parcelas é de {moeda(resultado.get('impacto_mensal', 0))}. "
            "Seu nível de parcelamento está alto. "
            "A prioridade deve ser reduzir os maiores compromissos antes de comprar novamente a prazo."
        )

    return (
        f"O impacto mensal das parcelas é de {moeda(resultado.get('impacto_mensal', 0))}. "
        "Seu nível de parcelamento está crítico. "
        "Não é recomendado assumir novas parcelas até reduzir significativamente o peso mensal."
    )
