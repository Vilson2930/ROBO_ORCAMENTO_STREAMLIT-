# ============================================================
# ROTATIVO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão profissional — decisão do cliente
# ============================================================

import re
import pandas as pd


def moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def simular_juros_compostos(saldo, juros_mensal=0.12, meses=12):
    saldo_inicial = float(saldo or 0)
    saldo_atual = saldo_inicial
    linhas = []

    for mes in range(1, meses + 1):
        saldo_atual *= (1 + juros_mensal)
        linhas.append({
            "mês": mes,
            "saldo_estimado": round(saldo_atual, 2),
            "juros_acumulado": round(saldo_atual - saldo_inicial, 2)
        })

    return pd.DataFrame(linhas)


def classificar_comprometimento_renda(percentual):
    if percentual <= 10:
        return "🟢 Saudável"
    if percentual <= 20:
        return "🟡 Atenção"
    if percentual <= 30:
        return "🟠 Alto"
    return "🔴 Crítico"


def analisar_pagamento_fatura(
    valor_fatura,
    pagamento_realizado,
    pagamento_minimo=None,
    renda_mensal=None,
    juros_mensal=0.12,
    meses=12
):
    valor_fatura = float(valor_fatura or 0)
    pagamento_realizado = float(pagamento_realizado or 0)
    pagamento_minimo = float(pagamento_minimo or 0)
    renda_mensal = float(renda_mensal or 0)

    saldo_financiado = max(valor_fatura - pagamento_realizado, 0)

    percentual_pago = (
        pagamento_realizado / valor_fatura * 100
        if valor_fatura > 0 else 0
    )

    peso_na_renda = (
        pagamento_realizado / renda_mensal * 100
        if renda_mensal > 0 else 0
    )

    saldo_na_renda = (
        saldo_financiado / renda_mensal * 100
        if renda_mensal > 0 else 0
    )

    if saldo_financiado <= 0:
        status = "🟢 Pagamento integral"
        classificacao = "SAUDÁVEL"
        mensagem = "Você pagou a fatura inteira. Não há saldo financiado nem juros estimados."
        acao = "Mantenha esse padrão sempre que possível."

    elif pagamento_minimo > 0 and pagamento_realizado <= pagamento_minimo * 1.05:
        status = "🔴 Pagamento mínimo"
        classificacao = "CRÍTICO"
        mensagem = "Você pagou apenas o mínimo ou muito próximo disso. A maior parte da fatura virou dívida com juros."
        acao = "Prioridade máxima: pagar o saldo financiado antes de novas compras."

    elif pagamento_realizado < valor_fatura:
        status = "🟠 Pagamento parcial"
        classificacao = "ALTO"
        mensagem = "Você pagou apenas parte da fatura. O restante poderá gerar juros no próximo ciclo."
        acao = "Quite o saldo financiado o mais rápido possível."

    else:
        status = "🟡 Atenção"
        classificacao = "ATENÇÃO"
        mensagem = "Existe risco financeiro, mas os dados precisam ser revisados."
        acao = "Confira a fatura e evite carregar saldo para o próximo mês."

    simulacao = simular_juros_compostos(
        saldo=saldo_financiado,
        juros_mensal=juros_mensal,
        meses=meses
    )

    custo_30 = 0
    custo_90 = 0
    custo_180 = 0
    custo_360 = 0

    saldo_30 = saldo_financiado
    saldo_90 = saldo_financiado
    saldo_180 = saldo_financiado
    saldo_360 = saldo_financiado

    if not simulacao.empty:
        if len(simulacao) >= 1:
            saldo_30 = float(simulacao.iloc[0]["saldo_estimado"])
            custo_30 = float(simulacao.iloc[0]["juros_acumulado"])

        if len(simulacao) >= 3:
            saldo_90 = float(simulacao.iloc[2]["saldo_estimado"])
            custo_90 = float(simulacao.iloc[2]["juros_acumulado"])

        if len(simulacao) >= 6:
            saldo_180 = float(simulacao.iloc[5]["saldo_estimado"])
            custo_180 = float(simulacao.iloc[5]["juros_acumulado"])

        if len(simulacao) >= 12:
            saldo_360 = float(simulacao.iloc[11]["saldo_estimado"])
            custo_360 = float(simulacao.iloc[11]["juros_acumulado"])

    return {
        "valor_fatura": valor_fatura,
        "pagamento_realizado": pagamento_realizado,
        "pagamento_minimo": pagamento_minimo,
        "renda_mensal": renda_mensal,

        "saldo_financiado": saldo_financiado,
        "percentual_pago": percentual_pago,
        "peso_pagamento_na_renda": peso_na_renda,
        "peso_saldo_na_renda": saldo_na_renda,

        "juros_mensal": juros_mensal,
        "status": status,
        "classificacao": classificacao,
        "mensagem": mensagem,
        "acao": acao,

        "saldo_30": saldo_30,
        "saldo_90": saldo_90,
        "saldo_180": saldo_180,
        "saldo_360": saldo_360,

        "custo_30": custo_30,
        "custo_90": custo_90,
        "custo_180": custo_180,
        "custo_360": custo_360,

        "simulacao": simulacao
    }


def simular_pagamento_minimo(
    valor_fatura,
    pagamento_minimo,
    renda_mensal=None,
    juros_mensal=0.12
):
    return analisar_pagamento_fatura(
        valor_fatura=valor_fatura,
        pagamento_realizado=pagamento_minimo,
        pagamento_minimo=pagamento_minimo,
        renda_mensal=renda_mensal,
        juros_mensal=juros_mensal,
        meses=12
    )


def simular_pagamento_metade(
    valor_fatura,
    renda_mensal=None,
    juros_mensal=0.12
):
    pagamento = float(valor_fatura or 0) * 0.50

    return analisar_pagamento_fatura(
        valor_fatura=valor_fatura,
        pagamento_realizado=pagamento,
        pagamento_minimo=None,
        renda_mensal=renda_mensal,
        juros_mensal=juros_mensal,
        meses=12
    )


def simular_nova_parcela(
    parcela_atual_mensal,
    nova_compra_valor,
    quantidade_parcelas,
    renda_mensal=None
):
    parcela_atual_mensal = float(parcela_atual_mensal or 0)
    nova_compra_valor = float(nova_compra_valor or 0)
    quantidade_parcelas = int(quantidade_parcelas or 1)
    renda_mensal = float(renda_mensal or 0)

    nova_parcela = (
        nova_compra_valor / quantidade_parcelas
        if quantidade_parcelas > 0 else nova_compra_valor
    )

    impacto_total_mensal = parcela_atual_mensal + nova_parcela

    peso_atual = (
        parcela_atual_mensal / renda_mensal * 100
        if renda_mensal > 0 else 0
    )

    peso_novo = (
        impacto_total_mensal / renda_mensal * 100
        if renda_mensal > 0 else 0
    )

    nivel = classificar_comprometimento_renda(peso_novo)

    if peso_novo <= 10:
        recomendacao = "Compra possível, mas ainda deve ter objetivo claro."
    elif peso_novo <= 20:
        recomendacao = "Atenção. A nova parcela reduz sua margem financeira."
    elif peso_novo <= 30:
        recomendacao = "Não recomendado. O comprometimento mensal ficará alto."
    else:
        recomendacao = "Evite. A compra deixaria seu orçamento em zona crítica."

    return {
        "parcela_atual_mensal": parcela_atual_mensal,
        "nova_compra_valor": nova_compra_valor,
        "quantidade_parcelas": quantidade_parcelas,
        "nova_parcela": nova_parcela,
        "impacto_total_mensal": impacto_total_mensal,
        "peso_atual_na_renda": peso_atual,
        "peso_novo_na_renda": peso_novo,
        "nivel": nivel,
        "recomendacao": recomendacao
    }


def gerar_texto_decisao_pagamento(resultado):
    if resultado["saldo_financiado"] <= 0:
        return (
            "✅ Você pagou a fatura integralmente.\n\n"
            "Não há juros estimados nem saldo financiado."
        )

    return (
        f"{resultado['status']}\n\n"
        f"Valor da fatura: {moeda(resultado['valor_fatura'])}\n"
        f"Valor pago: {moeda(resultado['pagamento_realizado'])}\n"
        f"Saldo que virou dívida: {moeda(resultado['saldo_financiado'])}\n\n"
        f"Com juros de {resultado['juros_mensal'] * 100:.1f}% ao mês:\n"
        f"Em 30 dias: {moeda(resultado['saldo_30'])}\n"
        f"Em 90 dias: {moeda(resultado['saldo_90'])}\n"
        f"Em 180 dias: {moeda(resultado['saldo_180'])}\n"
        f"Em 12 meses: {moeda(resultado['saldo_360'])}\n\n"
        f"Custo extra estimado em 12 meses: {moeda(resultado['custo_360'])}\n\n"
        f"Recomendação: {resultado['acao']}"
    )
