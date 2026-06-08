import pandas as pd
import re


PALAVRAS_PAGAMENTO_PARCIAL = [
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "PAGTO MINIMO",
    "PAGTO MÍNIMO",
    "PAGAMENTO PARCIAL",
    "PGTO PARCIAL",
]

PALAVRAS_SALDO_FINANCIADO = [
    "SALDO FINANCIADO",
    "SALDO DEVEDOR",
    "SALDO REMANESCENTE",
    "VALOR FINANCIADO",
    "FINANCIAMENTO FATURA",
    "PARCELAMENTO FATURA",
    "PARCELAMENTO DE FATURA",
    "CREDITO ROTATIVO",
    "CRÉDITO ROTATIVO",
    "ROTATIVO",
]

PALAVRAS_JUROS = [
    "JUROS",
    "JUROS ROTATIVO",
    "JUROS DE ROTATIVO",
    "JUROS FINANCIAMENTO",
    "JUROS DE FINANCIAMENTO",
]

PALAVRAS_IOF = [
    "IOF",
    "IOF FINANCIAMENTO",
    "IOF ROTATIVO",
]

PALAVRAS_MULTA = [
    "MULTA",
    "MULTA ATRASO",
    "MULTA POR ATRASO",
]

PALAVRAS_ENCARGOS = [
    "ENCARGOS",
    "ENCARGOS FINANCEIROS",
    "ENCARGOS CONTRATUAIS",
    "MORA",
]


def _normalizar_texto(texto):
    if pd.isna(texto):
        return ""

    texto = str(texto).upper()
    texto = texto.replace("Á", "A")
    texto = texto.replace("À", "A")
    texto = texto.replace("Ã", "A")
    texto = texto.replace("Â", "A")
    texto = texto.replace("É", "E")
    texto = texto.replace("Ê", "E")
    texto = texto.replace("Í", "I")
    texto = texto.replace("Ó", "O")
    texto = texto.replace("Õ", "O")
    texto = texto.replace("Ô", "O")
    texto = texto.replace("Ú", "U")
    texto = texto.replace("Ç", "C")

    return texto.strip()


def _contem(texto, lista_palavras):
    texto = _normalizar_texto(texto)
    lista_normalizada = [_normalizar_texto(p) for p in lista_palavras]

    return any(palavra in texto for palavra in lista_normalizada)


def _encontrar_coluna_texto(df):
    candidatos = [
        "descricao",
        "descrição",
        "compra",
        "merchant",
        "estabelecimento",
        "historico",
        "histórico",
        "lançamento",
        "lancamento",
        "texto",
        "categoria",
    ]

    for col in df.columns:
        if str(col).lower() in candidatos:
            return col

    for col in df.columns:
        if df[col].dtype == "object":
            return col

    return None


def _encontrar_coluna_valor(df):
    numericas = df.select_dtypes(include="number").columns.tolist()

    if not numericas:
        return None

    prioridade = [
        "valor",
        "valor_total",
        "total",
        "amount",
        "preco",
        "preço",
        "gasto",
    ]

    for palavra in prioridade:
        for col in numericas:
            if palavra in str(col).lower():
                return col

    return numericas[0]


def _somar_por_palavras(df, coluna_texto, coluna_valor, palavras):
    if df.empty or coluna_texto is None or coluna_valor is None:
        return 0.0

    mascara = df[coluna_texto].apply(lambda x: _contem(x, palavras))
    valores = pd.to_numeric(df.loc[mascara, coluna_valor], errors="coerce").fillna(0)

    return float(valores.sum())


def _filtrar_por_palavras(df, coluna_texto, palavras):
    if df.empty or coluna_texto is None:
        return pd.DataFrame()

    mascara = df[coluna_texto].apply(lambda x: _contem(x, palavras))
    return df.loc[mascara].copy()


def analisar_divida_cartao(df_transacoes):
    """
    Analisa sinais de dívida, rotativo, pagamento mínimo, juros, IOF,
    multa e encargos dentro das transações da fatura.

    Retorna um dicionário pronto para ser usado no app.py.
    """

    if df_transacoes is None or df_transacoes.empty:
        return {
            "risco_detectado": False,
            "nivel_risco": "🟢 Saudável",
            "score_penalidade": 0,
            "pagamento_parcial": 0.0,
            "saldo_financiado": 0.0,
            "juros": 0.0,
            "iof": 0.0,
            "multa": 0.0,
            "encargos": 0.0,
            "custo_total_divida": 0.0,
            "mensagem": "Nenhum dado de dívida foi encontrado.",
            "acoes_recomendadas": [],
            "linhas_detectadas": pd.DataFrame(),
        }

    df = df_transacoes.copy()

    coluna_texto = _encontrar_coluna_texto(df)
    coluna_valor = _encontrar_coluna_valor(df)

    if coluna_texto is None or coluna_valor is None:
        return {
            "risco_detectado": False,
            "nivel_risco": "🟡 Atenção",
            "score_penalidade": 5,
            "pagamento_parcial": 0.0,
            "saldo_financiado": 0.0,
            "juros": 0.0,
            "iof": 0.0,
            "multa": 0.0,
            "encargos": 0.0,
            "custo_total_divida": 0.0,
            "mensagem": "Não foi possível auditar dívida porque o motor não encontrou coluna de descrição ou valor.",
            "acoes_recomendadas": [
                "Revisar estrutura das transações extraídas.",
                "Validar nomes das colunas do dataframe.",
            ],
            "linhas_detectadas": pd.DataFrame(),
        }

    df[coluna_valor] = pd.to_numeric(df[coluna_valor], errors="coerce").fillna(0)

    pagamento_parcial = _somar_por_palavras(
        df, coluna_texto, coluna_valor, PALAVRAS_PAGAMENTO_PARCIAL
    )

    saldo_financiado = _somar_por_palavras(
        df, coluna_texto, coluna_valor, PALAVRAS_SALDO_FINANCIADO
    )

    juros = _somar_por_palavras(
        df, coluna_texto, coluna_valor, PALAVRAS_JUROS
    )

    iof = _somar_por_palavras(
        df, coluna_texto, coluna_valor, PALAVRAS_IOF
    )

    multa = _somar_por_palavras(
        df, coluna_texto, coluna_valor, PALAVRAS_MULTA
    )

    encargos = _somar_por_palavras(
        df, coluna_texto, coluna_valor, PALAVRAS_ENCARGOS
    )

    custo_total_divida = juros + iof + multa + encargos

    linhas_pagamento = _filtrar_por_palavras(df, coluna_texto, PALAVRAS_PAGAMENTO_PARCIAL)
    linhas_saldo = _filtrar_por_palavras(df, coluna_texto, PALAVRAS_SALDO_FINANCIADO)
    linhas_juros = _filtrar_por_palavras(df, coluna_texto, PALAVRAS_JUROS)
    linhas_iof = _filtrar_por_palavras(df, coluna_texto, PALAVRAS_IOF)
    linhas_multa = _filtrar_por_palavras(df, coluna_texto, PALAVRAS_MULTA)
    linhas_encargos = _filtrar_por_palavras(df, coluna_texto, PALAVRAS_ENCARGOS)

    linhas_detectadas = pd.concat(
        [
            linhas_pagamento,
            linhas_saldo,
            linhas_juros,
            linhas_iof,
            linhas_multa,
            linhas_encargos,
        ],
        ignore_index=True
    ).drop_duplicates()

    risco_detectado = any([
        pagamento_parcial > 0,
        saldo_financiado > 0,
        juros > 0,
        iof > 0,
        multa > 0,
        encargos > 0,
    ])

    score_penalidade = 0

    if pagamento_parcial > 0:
        score_penalidade += 15

    if saldo_financiado > 0:
        score_penalidade += 25

    if juros > 0:
        score_penalidade += 20

    if iof > 0:
        score_penalidade += 5

    if multa > 0:
        score_penalidade += 10

    if encargos > 0:
        score_penalidade += 10

    score_penalidade = min(score_penalidade, 60)

    if not risco_detectado:
        nivel_risco = "🟢 Saudável"
        mensagem = "Nenhum sinal relevante de dívida, rotativo, juros ou encargos foi detectado."
        acoes = [
            "Manter pagamento integral da fatura.",
            "Evitar parcelamentos desnecessários.",
            "Acompanhar mensalmente a evolução dos gastos.",
        ]

    elif saldo_financiado > 0 or juros > 0 or encargos > 0:
        nivel_risco = "🔴 Risco crítico"
        mensagem = (
            "Foram encontrados sinais de crédito rotativo, saldo financiado, "
            "juros ou encargos. A prioridade financeira deve ser quitar o saldo "
            "pendente antes de assumir novas compras."
        )
        acoes = [
            "Prioridade máxima: quitar o saldo financiado.",
            "Evitar novas compras no cartão até regularizar a fatura.",
            "Não assumir novas parcelas neste momento.",
            "Negociar a dívida se o saldo não puder ser quitado integralmente.",
        ]

    elif pagamento_parcial > 0:
        nivel_risco = "🟠 Atenção elevada"
        mensagem = (
            "Foi identificado pagamento parcial ou pagamento mínimo da fatura. "
            "Isso pode gerar juros no próximo ciclo."
        )
        acoes = [
            "Quitar o restante da fatura o quanto antes.",
            "Evitar pagar apenas o mínimo novamente.",
            "Reduzir gastos variáveis no próximo mês.",
        ]

    else:
        nivel_risco = "🟡 Atenção"
        mensagem = (
            "Existem sinais financeiros que precisam ser acompanhados, "
            "mas ainda não há evidência forte de rotativo crítico."
        )
        acoes = [
            "Revisar lançamentos financeiros.",
            "Acompanhar juros, IOF e encargos na próxima fatura.",
        ]

    return {
        "risco_detectado": risco_detectado,
        "nivel_risco": nivel_risco,
        "score_penalidade": score_penalidade,
        "pagamento_parcial": pagamento_parcial,
        "saldo_financiado": saldo_financiado,
        "juros": juros,
        "iof": iof,
        "multa": multa,
        "encargos": encargos,
        "custo_total_divida": custo_total_divida,
        "mensagem": mensagem,
        "acoes_recomendadas": acoes,
        "linhas_detectadas": linhas_detectadas,
    }


def ajustar_score_por_divida(score_original, resultado_divida):
    try:
        score = float(score_original)
    except Exception:
        score = 0

    penalidade = resultado_divida.get("score_penalidade", 0)

    score_ajustado = max(0, score - penalidade)

    return round(score_ajustado, 0)


def gerar_texto_divida(resultado):
    if not resultado.get("risco_detectado", False):
        return (
            "Nenhum sinal relevante de dívida de cartão foi detectado. "
            "O cliente aparenta estar fora do crédito rotativo."
        )

    texto = f"{resultado.get('nivel_risco')} detectado.\n\n"

    texto += f"Pagamento parcial/mínimo: R$ {resultado.get('pagamento_parcial', 0):,.2f}\n"
    texto += f"Saldo financiado: R$ {resultado.get('saldo_financiado', 0):,.2f}\n"
    texto += f"Juros: R$ {resultado.get('juros', 0):,.2f}\n"
    texto += f"IOF: R$ {resultado.get('iof', 0):,.2f}\n"
    texto += f"Multa: R$ {resultado.get('multa', 0):,.2f}\n"
    texto += f"Encargos: R$ {resultado.get('encargos', 0):,.2f}\n"
    texto += f"Custo total da dívida: R$ {resultado.get('custo_total_divida', 0):,.2f}\n\n"

    texto += resultado.get("mensagem", "")

    return texto
