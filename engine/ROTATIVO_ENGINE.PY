# ============================================================
# ROTATIVO ENGINE
# ORÇAMENTO INTELIGENTE
# Detecta pagamento mínimo/parcial e simula juros do cartão
# ============================================================

import re
import pandas as pd


def moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


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


def encontrar_coluna_texto(df):
    candidatos = [
        "descricao_original",
        "descricao",
        "descrição",
        "merchant",
        "estabelecimento",
        "compra",
        "texto",
        "lancamento",
        "lançamento",
    ]

    for col in candidatos:
        if col in df.columns:
            return col

    for col in df.columns:
        if df[col].dtype == "object":
            return col

    return None


def encontrar_coluna_valor(df):
    candidatos = [
        "valor",
        "valor_total",
        "total",
        "amount",
        "gasto",
        "preco",
        "preço",
    ]

    for col in candidatos:
        if col in df.columns:
            return col

    numericas = df.select_dtypes(include="number").columns.tolist()

    return numericas[0] if numericas else None


def somar_por_termos(df, coluna_texto, coluna_valor, termos):
    if df is None or df.empty:
        return 0

    termos_norm = [normalizar_texto(t) for t in termos]

    def contem(texto):
        texto = normalizar_texto(texto)
        return any(t in texto for t in termos_norm)

    filtro = df[coluna_texto].apply(contem)

    return float(
        pd.to_numeric(
            df.loc[filtro, coluna_valor],
            errors="coerce"
        ).fillna(0).sum()
    )


def linhas_por_termos(df, coluna_texto, termos):
    if df is None or df.empty:
        return pd.DataFrame()

    termos_norm = [normalizar_texto(t) for t in termos]

    def contem(texto):
        texto = normalizar_texto(texto)
        return any(t in texto for t in termos_norm)

    return df[df[coluna_texto].apply(contem)].copy()


def simular_juros_rotativo(
    saldo_financiado,
    juros_mensal=0.12,
    meses=6
):
    """
    Simula juros compostos do rotativo.

    juros_mensal:
    0.12 = 12% ao mês
    """

    saldo = float(saldo_financiado or 0)
    juros_mensal = float(juros_mensal or 0)

    linhas = []

    for mes in range(1, meses + 1):
        saldo = saldo * (1 + juros_mensal)
        juros_acumulado = saldo - float(saldo_financiado or 0)

        linhas.append({
            "mes": mes,
            "saldo_estimado": round(saldo, 2),
            "juros_acumulado": round(juros_acumulado, 2)
        })

    return pd.DataFrame(linhas)


def analisar_rotativo(
    df_transacoes,
    valor_fatura=None,
    pagamento_realizado=None,
    juros_mensal=0.12
):
    """
    Analisa risco de rotativo.

    Pode funcionar de duas formas:

    1. Automática:
       tenta encontrar pagamento mínimo, saldo financiado, juros, IOF, encargos na fatura.

    2. Manual:
       se o app informar valor_fatura e pagamento_realizado,
       calcula saldo financiado automaticamente.
    """

    termos_pagamento_minimo = [
        "PAGAMENTO MINIMO",
        "PAGAMENTO MÍNIMO",
        "PAGTO MINIMO",
        "PAGTO MÍNIMO",
        "MINIMO DA FATURA",
        "MÍNIMO DA FATURA",
    ]

    termos_pagamento_parcial = [
        "PAGAMENTO PARCIAL",
        "PGTO PARCIAL",
        "PAGTO PARCIAL",
    ]

    termos_saldo_financiado = [
        "SALDO FINANCIADO",
        "SALDO DEVEDOR",
        "SALDO REMANESCENTE",
        "VALOR FINANCIADO",
        "CREDITO ROTATIVO",
        "CRÉDITO ROTATIVO",
        "ROTATIVO",
        "FINANCIAMENTO FATURA",
        "PARCELAMENTO FATURA",
        "PARCELAMENTO DE FATURA",
    ]

    termos_juros = [
        "JUROS",
        "JUROS ROTATIVO",
        "JUROS DE ROTATIVO",
        "JUROS FINANCIAMENTO",
        "JUROS DE FINANCIAMENTO",
    ]

    termos_iof = [
        "IOF",
        "IOF FINANCIAMENTO",
        "IOF ROTATIVO",
    ]

    termos_multa = [
        "MULTA",
        "MULTA ATRASO",
        "MULTA POR ATRASO",
        "MORA",
    ]

    termos_encargos = [
        "ENCARGOS",
        "ENCARGOS FINANCEIROS",
        "ENCARGOS CONTRATUAIS",
    ]

    if df_transacoes is None or df_transacoes.empty:
        df_transacoes = pd.DataFrame()

    coluna_texto = encontrar_coluna_texto(df_transacoes) if not df_transacoes.empty else None
    coluna_valor = encontrar_coluna_valor(df_transacoes) if not df_transacoes.empty else None

    pagamento_minimo = 0
    pagamento_parcial = 0
    saldo_detectado = 0
    juros_detectados = 0
    iof_detectado = 0
    multa_detectada = 0
    encargos_detectados = 0
    linhas_detectadas = pd.DataFrame()

    if coluna_texto and coluna_valor:
        df = df_transacoes.copy()
        df[coluna_valor] = pd.to_numeric(df[coluna_valor], errors="coerce").fillna(0)

        pagamento_minimo = somar_por_termos(df, coluna_texto, coluna_valor, termos_pagamento_minimo)
        pagamento_parcial = somar_por_termos(df, coluna_texto, coluna_valor, termos_pagamento_parcial)
        saldo_detectado = somar_por_termos(df, coluna_texto, coluna_valor, termos_saldo_financiado)
        juros_detectados = somar_por_termos(df, coluna_texto, coluna_valor, termos_juros)
        iof_detectado = somar_por_termos(df, coluna_texto, coluna_valor, termos_iof)
        multa_detectada = somar_por_termos(df, coluna_texto, coluna_valor, termos_multa)
        encargos_detectados = somar_por_termos(df, coluna_texto, coluna_valor, termos_encargos)

        linhas_detectadas = pd.concat(
            [
                linhas_por_termos(df, coluna_texto, termos_pagamento_minimo),
                linhas_por_termos(df, coluna_texto, termos_pagamento_parcial),
                linhas_por_termos(df, coluna_texto, termos_saldo_financiado),
                linhas_por_termos(df, coluna_texto, termos_juros),
                linhas_por_termos(df, coluna_texto, termos_iof),
                linhas_por_termos(df, coluna_texto, termos_multa),
                linhas_por_termos(df, coluna_texto, termos_encargos),
            ],
            ignore_index=True
        ).drop_duplicates()

    saldo_manual = 0

    if valor_fatura is not None and pagamento_realizado is not None:
        saldo_manual = max(
            float(valor_fatura) - float(pagamento_realizado),
            0
        )

    saldo_financiado = max(
        float(saldo_detectado or 0),
        float(saldo_manual or 0)
    )

    custo_financeiro_detectado = (
        juros_detectados +
        iof_detectado +
        multa_detectada +
        encargos_detectados
    )

    risco_detectado = any([
        pagamento_minimo > 0,
        pagamento_parcial > 0,
        saldo_financiado > 0,
        juros_detectados > 0,
        iof_detectado > 0,
        multa_detectada > 0,
        encargos_detectados > 0,
    ])

    simulacao = simular_juros_rotativo(
        saldo_financiado=saldo_financiado,
        juros_mensal=juros_mensal,
        meses=6
    ) if saldo_financiado > 0 else pd.DataFrame()

    if not risco_detectado:
        nivel = "🟢 Sem rotativo detectado"
        classificacao = "SAUDÁVEL"
        mensagem = (
            "Nenhum sinal relevante de pagamento mínimo, saldo financiado, "
            "juros ou encargos foi detectado."
        )
        acao = "Mantenha o pagamento integral da fatura para evitar juros."

    elif saldo_financiado > 0 and pagamento_minimo > 0:
        nivel = "🔴 Pagamento mínimo detectado"
        classificacao = "CRÍTICO"
        mensagem = (
            f"Foi detectado pagamento mínimo e saldo financiado de {moeda(saldo_financiado)}. "
            "Isso pode gerar juros elevados nos próximos meses."
        )
        acao = "Prioridade máxima: quitar o saldo financiado o quanto antes."

    elif saldo_financiado > 0:
        nivel = "🟠 Pagamento parcial / saldo financiado"
        classificacao = "ALTO"
        mensagem = (
            f"Existe saldo financiado estimado de {moeda(saldo_financiado)}. "
            "Esse valor pode crescer com juros se não for quitado."
        )
        acao = "Evite novas compras no cartão e quite o saldo em aberto."

    elif custo_financeiro_detectado > 0:
        nivel = "🟠 Custo financeiro detectado"
        classificacao = "ALTO"
        mensagem = (
            f"Foram detectados {moeda(custo_financeiro_detectado)} em juros, IOF, multa ou encargos."
        )
        acao = "Revise a fatura e evite carregar saldo para o próximo mês."

    else:
        nivel = "🟡 Atenção"
        classificacao = "ATENÇÃO"
        mensagem = "Há sinais de risco financeiro, mas sem saldo financiado claro."
        acao = "Acompanhe a próxima fatura e evite pagamento parcial."

    custo_30_dias = 0
    custo_90_dias = 0
    saldo_30_dias = saldo_financiado
    saldo_90_dias = saldo_financiado

    if not simulacao.empty:
        linha_1 = simulacao[simulacao["mes"] == 1]
        linha_3 = simulacao[simulacao["mes"] == 3]

        if not linha_1.empty:
            saldo_30_dias = float(linha_1.iloc[0]["saldo_estimado"])
            custo_30_dias = float(linha_1.iloc[0]["juros_acumulado"])

        if not linha_3.empty:
            saldo_90_dias = float(linha_3.iloc[0]["saldo_estimado"])
            custo_90_dias = float(linha_3.iloc[0]["juros_acumulado"])

    return {
        "risco_detectado": risco_detectado,
        "nivel": nivel,
        "classificacao": classificacao,

        "valor_fatura": float(valor_fatura or 0),
        "pagamento_realizado": float(pagamento_realizado or 0),
        "pagamento_minimo_detectado": pagamento_minimo,
        "pagamento_parcial_detectado": pagamento_parcial,

        "saldo_financiado": saldo_financiado,
        "juros_detectados": juros_detectados,
        "iof_detectado": iof_detectado,
        "multa_detectada": multa_detectada,
        "encargos_detectados": encargos_detectados,
        "custo_financeiro_detectado": custo_financeiro_detectado,

        "juros_mensal": juros_mensal,
        "saldo_30_dias": saldo_30_dias,
        "saldo_90_dias": saldo_90_dias,
        "custo_30_dias": custo_30_dias,
        "custo_90_dias": custo_90_dias,

        "mensagem": mensagem,
        "acao": acao,

        "simulacao": simulacao,
        "linhas_detectadas": linhas_detectadas
    }


def simular_pagamento_parcial(
    valor_fatura,
    pagamento_realizado,
    juros_mensal=0.12,
    meses=6
):
    saldo_financiado = max(
        float(valor_fatura or 0) - float(pagamento_realizado or 0),
        0
    )

    simulacao = simular_juros_rotativo(
        saldo_financiado=saldo_financiado,
        juros_mensal=juros_mensal,
        meses=meses
    )

    return {
        "valor_fatura": float(valor_fatura or 0),
        "pagamento_realizado": float(pagamento_realizado or 0),
        "saldo_financiado": saldo_financiado,
        "juros_mensal": juros_mensal,
        "simulacao": simulacao
    }


def gerar_texto_rotativo(resultado):
    if not resultado.get("risco_detectado", False):
        return (
            "Nenhum sinal de rotativo foi detectado. "
            "O ideal é manter o pagamento integral da fatura."
        )

    return (
        f"{resultado.get('nivel')}.\n\n"
        f"Saldo financiado estimado: {moeda(resultado.get('saldo_financiado', 0))}.\n"
        f"Juros mensal usado na simulação: {resultado.get('juros_mensal', 0) * 100:.1f}%.\n"
        f"Em 30 dias, o saldo pode chegar a {moeda(resultado.get('saldo_30_dias', 0))}.\n"
        f"Em 90 dias, o saldo pode chegar a {moeda(resultado.get('saldo_90_dias', 0))}.\n"
        f"Custo estimado em 90 dias: {moeda(resultado.get('custo_90_dias', 0))}.\n\n"
        f"Recomendação: {resultado.get('acao', '')}"
    )
