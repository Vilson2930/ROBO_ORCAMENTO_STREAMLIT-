# ============================================================
# ROTATIVO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão profissional — decisão do cliente
# ============================================================

import re
import pandas as pd


# ============================================================
# FORMATAÇÃO
# ============================================================

def moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def percentual(valor):
    try:
        return f"{float(valor):.1f}%"
    except Exception:
        return "0,0%"


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_texto(texto):
    texto = str(texto or "").upper()

    trocas = {
        "Á": "A", "À": "A", "Ã": "A", "Â": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Õ": "O", "Ô": "O",
        "Ú": "U",
        "Ç": "C",
    }

    for a, b in trocas.items():
        texto = texto.replace(a, b)

    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def converter_valor(valor):
    try:
        if isinstance(valor, str):
            valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(valor)
    except Exception:
        return 0.0


# ============================================================
# SIMULAÇÃO DE JUROS
# ============================================================

def simular_juros_compostos(saldo, juros_mensal=0.12, meses=12):
    saldo_inicial = converter_valor(saldo)
    juros_mensal = converter_valor(juros_mensal)
    meses = int(meses or 12)

    saldo_atual = saldo_inicial
    linhas = []

    for mes in range(1, meses + 1):
        saldo_atual *= (1 + juros_mensal)

        linhas.append({
            "mes": mes,
            "saldo_estimado": round(saldo_atual, 2),
            "juros_acumulado": round(saldo_atual - saldo_inicial, 2),
            "saldo_formatado": moeda(saldo_atual),
            "juros_formatado": moeda(saldo_atual - saldo_inicial)
        })

    return pd.DataFrame(linhas)


# ============================================================
# CLASSIFICAÇÕES
# ============================================================

def classificar_comprometimento_renda(percentual_renda):
    percentual_renda = converter_valor(percentual_renda)

    if percentual_renda <= 10:
        return "🟢 Saudável"
    if percentual_renda <= 20:
        return "🟡 Atenção"
    if percentual_renda <= 30:
        return "🟠 Alto"
    return "🔴 Crítico"


def classificar_status_pagamento(valor_fatura, pagamento_realizado, pagamento_minimo):
    valor_fatura = converter_valor(valor_fatura)
    pagamento_realizado = converter_valor(pagamento_realizado)
    pagamento_minimo = converter_valor(pagamento_minimo)

    saldo_financiado = max(valor_fatura - pagamento_realizado, 0)

    if valor_fatura <= 0:
        return "SEM DADOS", "⚪ Sem dados"

    if saldo_financiado <= 0:
        return "SAUDÁVEL", "🟢 Pagamento integral"

    if pagamento_minimo > 0 and pagamento_realizado <= pagamento_minimo * 1.05:
        return "CRÍTICO", "🔴 Pagamento mínimo"

    if pagamento_realizado > 0 and pagamento_realizado < valor_fatura:
        return "ALTO", "🟠 Pagamento parcial"

    if pagamento_realizado <= 0:
        return "CRÍTICO", "🔴 Fatura não paga"

    return "ATENÇÃO", "🟡 Atenção"


# ============================================================
# ANÁLISE PRINCIPAL DA FATURA
# ============================================================

def analisar_pagamento_fatura(
    valor_fatura,
    pagamento_realizado,
    pagamento_minimo=None,
    renda_mensal=None,
    juros_mensal=0.12,
    meses=12
):
    valor_fatura = converter_valor(valor_fatura)
    pagamento_realizado = converter_valor(pagamento_realizado)
    pagamento_minimo = converter_valor(pagamento_minimo)
    renda_mensal = converter_valor(renda_mensal)
    juros_mensal = converter_valor(juros_mensal)

    saldo_financiado = max(valor_fatura - pagamento_realizado, 0)

    percentual_pago = (
        pagamento_realizado / valor_fatura * 100
        if valor_fatura > 0
        else 0
    )

    percentual_nao_pago = (
        saldo_financiado / valor_fatura * 100
        if valor_fatura > 0
        else 0
    )

    peso_fatura_na_renda = (
        valor_fatura / renda_mensal * 100
        if renda_mensal > 0
        else 0
    )

    peso_pagamento_na_renda = (
        pagamento_realizado / renda_mensal * 100
        if renda_mensal > 0
        else 0
    )

    peso_saldo_na_renda = (
        saldo_financiado / renda_mensal * 100
        if renda_mensal > 0
        else 0
    )

    classificacao, status = classificar_status_pagamento(
        valor_fatura,
        pagamento_realizado,
        pagamento_minimo
    )

    if classificacao == "SAUDÁVEL":
        mensagem = (
            "Você pagou a fatura inteira. "
            "Não há saldo financiado nem juros estimados."
        )
        acao = "Mantenha esse padrão sempre que possível."

    elif classificacao == "CRÍTICO" and pagamento_realizado <= 0:
        mensagem = (
            "A fatura não foi paga. Todo o valor pode virar dívida com juros, multa e encargos."
        )
        acao = "Prioridade máxima: pagar o maior valor possível imediatamente."

    elif classificacao == "CRÍTICO":
        mensagem = (
            "Você pagou apenas o mínimo ou muito próximo disso. "
            "A maior parte da fatura virou dívida com juros."
        )
        acao = "Prioridade máxima: quitar o saldo financiado antes de novas compras."

    elif classificacao == "ALTO":
        mensagem = (
            "Você pagou apenas parte da fatura. "
            "O restante poderá gerar juros no próximo ciclo."
        )
        acao = "Quite o saldo financiado o mais rápido possível."

    else:
        mensagem = (
            "Existe risco financeiro, mas os dados precisam ser revisados."
        )
        acao = "Confira a fatura e evite carregar saldo para o próximo mês."

    simulacao = simular_juros_compostos(
        saldo=saldo_financiado,
        juros_mensal=juros_mensal,
        meses=meses
    )

    def pegar_mes(numero_mes):
        if simulacao.empty:
            return saldo_financiado, 0

        linha = simulacao[simulacao["mes"] == numero_mes]

        if linha.empty:
            return saldo_financiado, 0

        return (
            float(linha.iloc[0]["saldo_estimado"]),
            float(linha.iloc[0]["juros_acumulado"])
        )

    saldo_30, custo_30 = pegar_mes(1)
    saldo_90, custo_90 = pegar_mes(3)
    saldo_180, custo_180 = pegar_mes(6)
    saldo_360, custo_360 = pegar_mes(12)

    nivel_saldo_renda = classificar_comprometimento_renda(
        peso_saldo_na_renda
    )

    return {
        "valor_fatura": valor_fatura,
        "pagamento_realizado": pagamento_realizado,
        "pagamento_minimo": pagamento_minimo,
        "renda_mensal": renda_mensal,

        "saldo_financiado": saldo_financiado,
        "percentual_pago": percentual_pago,
        "percentual_nao_pago": percentual_nao_pago,

        "peso_fatura_na_renda": peso_fatura_na_renda,
        "peso_pagamento_na_renda": peso_pagamento_na_renda,
        "peso_saldo_na_renda": peso_saldo_na_renda,
        "nivel_saldo_renda": nivel_saldo_renda,

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


# ============================================================
# CENÁRIOS PADRÃO
# ============================================================

def simular_pagamento_integral(
    valor_fatura,
    renda_mensal=None,
    juros_mensal=0.12
):
    return analisar_pagamento_fatura(
        valor_fatura=valor_fatura,
        pagamento_realizado=valor_fatura,
        pagamento_minimo=None,
        renda_mensal=renda_mensal,
        juros_mensal=juros_mensal,
        meses=12
    )


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
    pagamento = converter_valor(valor_fatura) * 0.50

    return analisar_pagamento_fatura(
        valor_fatura=valor_fatura,
        pagamento_realizado=pagamento,
        pagamento_minimo=None,
        renda_mensal=renda_mensal,
        juros_mensal=juros_mensal,
        meses=12
    )


def simular_pagamento_percentual(
    valor_fatura,
    percentual_pagamento,
    pagamento_minimo=None,
    renda_mensal=None,
    juros_mensal=0.12
):
    valor_fatura = converter_valor(valor_fatura)
    percentual_pagamento = converter_valor(percentual_pagamento)

    pagamento = valor_fatura * (percentual_pagamento / 100)

    return analisar_pagamento_fatura(
        valor_fatura=valor_fatura,
        pagamento_realizado=pagamento,
        pagamento_minimo=pagamento_minimo,
        renda_mensal=renda_mensal,
        juros_mensal=juros_mensal,
        meses=12
    )


# ============================================================
# NOVA COMPRA PARCELADA
# ============================================================

def simular_nova_parcela(
    parcela_atual_mensal,
    nova_compra_valor,
    quantidade_parcelas,
    renda_mensal=None
):
    parcela_atual_mensal = converter_valor(parcela_atual_mensal)
    nova_compra_valor = converter_valor(nova_compra_valor)
    quantidade_parcelas = int(quantidade_parcelas or 1)
    renda_mensal = converter_valor(renda_mensal)

    if quantidade_parcelas <= 0:
        quantidade_parcelas = 1

    nova_parcela = nova_compra_valor / quantidade_parcelas
    impacto_total_mensal = parcela_atual_mensal + nova_parcela

    peso_atual = (
        parcela_atual_mensal / renda_mensal * 100
        if renda_mensal > 0
        else 0
    )

    peso_novo = (
        impacto_total_mensal / renda_mensal * 100
        if renda_mensal > 0
        else 0
    )

    aumento_mensal = nova_parcela
    aumento_percentual_renda = (
        nova_parcela / renda_mensal * 100
        if renda_mensal > 0
        else 0
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
        "aumento_mensal": aumento_mensal,
        "aumento_percentual_renda": aumento_percentual_renda,
        "nivel": nivel,
        "recomendacao": recomendacao
    }


# ============================================================
# TEXTOS PARA O CLIENTE
# ============================================================

def gerar_texto_decisao_pagamento(resultado):
    if resultado.get("saldo_financiado", 0) <= 0:
        return (
            "✅ Você pagou a fatura integralmente.\n\n"
            "Não há juros estimados nem saldo financiado.\n\n"
            f"Recomendação: {resultado.get('acao', '')}"
        )

    return (
        f"{resultado.get('status', '⚠️ Atenção')}\n\n"
        f"Valor da fatura: {moeda(resultado.get('valor_fatura', 0))}\n"
        f"Valor pago: {moeda(resultado.get('pagamento_realizado', 0))}\n"
        f"Saldo que virou dívida: {moeda(resultado.get('saldo_financiado', 0))}\n"
        f"Parte não paga: {percentual(resultado.get('percentual_nao_pago', 0))}\n\n"
        f"Com juros estimados de {resultado.get('juros_mensal', 0) * 100:.1f}% ao mês:\n"
        f"Em 30 dias: {moeda(resultado.get('saldo_30', 0))}\n"
        f"Em 90 dias: {moeda(resultado.get('saldo_90', 0))}\n"
        f"Em 180 dias: {moeda(resultado.get('saldo_180', 0))}\n"
        f"Em 12 meses: {moeda(resultado.get('saldo_360', 0))}\n\n"
        f"Custo extra estimado em 12 meses: {moeda(resultado.get('custo_360', 0))}\n\n"
        f"Recomendação: {resultado.get('acao', '')}"
    )


def gerar_resumo_comparativo(valor_fatura, pagamento_minimo, renda_mensal=None, juros_mensal=0.12):
    integral = simular_pagamento_integral(
        valor_fatura=valor_fatura,
        renda_mensal=renda_mensal,
        juros_mensal=juros_mensal
    )

    minimo = simular_pagamento_minimo(
        valor_fatura=valor_fatura,
        pagamento_minimo=pagamento_minimo,
        renda_mensal=renda_mensal,
        juros_mensal=juros_mensal
    )

    metade = simular_pagamento_metade(
        valor_fatura=valor_fatura,
        renda_mensal=renda_mensal,
        juros_mensal=juros_mensal
    )

    return pd.DataFrame([
        {
            "cenário": "Pagar integral",
            "valor_pago": integral["pagamento_realizado"],
            "saldo_financiado": integral["saldo_financiado"],
            "custo_12_meses": integral["custo_360"],
            "classificacao": integral["status"]
        },
        {
            "cenário": "Pagar mínimo",
            "valor_pago": minimo["pagamento_realizado"],
            "saldo_financiado": minimo["saldo_financiado"],
            "custo_12_meses": minimo["custo_360"],
            "classificacao": minimo["status"]
        },
        {
            "cenário": "Pagar metade",
            "valor_pago": metade["pagamento_realizado"],
            "saldo_financiado": metade["saldo_financiado"],
            "custo_12_meses": metade["custo_360"],
            "classificacao": metade["status"]
        }
    ])
