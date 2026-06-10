# ============================================================
# COMPROMISSOS ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — preservada + deduplicação profissional
#
# Corrige:
# - valores inflados vindos de conversão anterior, como 169.95 -> 16995
# - remove compromissos incompatíveis com o gasto analisado
# - recalcula valor_restante quando necessário
# - remove duplicatas reais antes da soma
# - preserva interface e nomes das funções atuais
# ============================================================

import pandas as pd


# ============================================================
# CONFIGURAÇÕES DE SANIDADE
# ============================================================

MAX_PARCELA_PADRAO = 10000.0
MAX_TOTAL_COMPRA_PADRAO = 500000.0
MAX_PARCELAS_ABERTAS = 60


# ============================================================
# FORMATAÇÃO
# ============================================================

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


def _converter_numero(valor):
    """
    Conversor seguro.
    Se já vier float/int, mantém.
    Se vier texto brasileiro, converte.
    Evita converter 169.95 para 16995.
    """
    if valor is None:
        return 0.0

    if isinstance(valor, (int, float)):
        try:
            return float(valor)
        except Exception:
            return 0.0

    texto = str(valor).strip()

    if not texto:
        return 0.0

    texto = texto.replace("R$", "").replace(" ", "")

    try:
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
            return float(texto)

        return float(texto)

    except Exception:
        return 0.0


def _normalizar_compra(texto):
    """
    Normaliza o nome da compra somente para comparação/deduplicação.
    Não altera o nome exibido na interface.
    """
    texto = str(texto or "").upper().strip()
    texto = texto.replace("•", "")
    texto = texto.replace("*", " ")
    texto = texto.replace("|", " ")
    texto = " ".join(texto.split())
    return texto


def _deduplicar_compromissos(df):
    """
    Remove duplicatas reais vindas de múltiplos leitores.

    Exemplo:
    O parcelamento_engine e outro leitor podem encontrar a mesma compra.
    Sem essa trava, o compromissos_engine soma duas vezes.
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    for col in ["compra", "status"]:
        if col not in df.columns:
            df[col] = "-"

    for col in ["valor_parcela", "parcelas_abertas", "valor_restante", "valor_total_compra"]:
        if col not in df.columns:
            df[col] = 0

    df["_compra_dedupe"] = df["compra"].apply(_normalizar_compra)
    df["_valor_parcela_dedupe"] = df["valor_parcela"].round(2)
    df["_valor_restante_dedupe"] = df["valor_restante"].round(2)
    df["_valor_total_compra_dedupe"] = df["valor_total_compra"].round(2)
    df["_parcelas_abertas_dedupe"] = df["parcelas_abertas"].astype(int)
    df["_status_dedupe"] = df["status"].astype(str).str.upper().str.strip()

    df = df.drop_duplicates(
        subset=[
            "_compra_dedupe",
            "_valor_parcela_dedupe",
            "_parcelas_abertas_dedupe",
            "_valor_restante_dedupe",
            "_valor_total_compra_dedupe",
            "_status_dedupe",
        ],
        keep="first"
    )

    df = df.drop(
        columns=[
            "_compra_dedupe",
            "_valor_parcela_dedupe",
            "_valor_restante_dedupe",
            "_valor_total_compra_dedupe",
            "_parcelas_abertas_dedupe",
            "_status_dedupe",
        ],
        errors="ignore"
    )

    return df


# ============================================================
# RESULTADO VAZIO
# ============================================================

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


# ============================================================
# TRAVA DE SANIDADE
# ============================================================

def _limpar_compromissos_absurdos(df, gasto_total=0, renda_mensal=None):
    """
    Remove linhas matematicamente incompatíveis.

    Exemplo do bug:
    gasto_total = 619.90
    valor_parcela = 16995.00

    Isso é impossível dentro de uma fatura-teste de R$ 619,90.
    """

    if df is None or df.empty:
        return df

    df = df.copy()

    for col in ["valor_restante", "valor_total_compra", "valor_parcela", "parcelas_abertas"]:
        if col not in df.columns:
            df[col] = 0

        df[col] = df[col].apply(_converter_numero)

    if "status" not in df.columns:
        df["status"] = "-"

    if "compra" not in df.columns:
        df["compra"] = "-"

    if "total_parcelas" not in df.columns:
        df["total_parcelas"] = 0

    df["total_parcelas"] = df["total_parcelas"].apply(_converter_numero).astype(int)
    df["parcelas_abertas"] = df["parcelas_abertas"].fillna(0).astype(int)

    # Recalcula valor_restante quando a estrutura permite.
    # Isso evita depender de valor_restante corrompido.
    mascara_recalculo = (
        (df["valor_parcela"] > 0) &
        (df["parcelas_abertas"] >= 0) &
        (df["parcelas_abertas"] <= MAX_PARCELAS_ABERTAS)
    )

    df.loc[mascara_recalculo, "valor_restante"] = (
        df.loc[mascara_recalculo, "valor_parcela"] *
        df.loc[mascara_recalculo, "parcelas_abertas"]
    )

    # Remove parcelas impossíveis.
    df = df[df["valor_parcela"] > 0].copy()
    df = df[df["valor_parcela"] <= MAX_PARCELA_PADRAO].copy()

    # Remove quantidade de parcelas absurda.
    df = df[df["parcelas_abertas"] >= 0].copy()
    df = df[df["parcelas_abertas"] <= MAX_PARCELAS_ABERTAS].copy()

    # Remove totais impossíveis.
    df = df[df["valor_restante"] >= 0].copy()
    df = df[df["valor_total_compra"] <= MAX_TOTAL_COMPRA_PADRAO].copy()

    # Trava contextual usando a fatura analisada.
    # Se uma parcela mensal for maior que 3x o gasto total da fatura, descarta.
    try:
        base = float(renda_mensal) if renda_mensal else float(gasto_total)
    except Exception:
        base = 0.0

    if base > 0:
        limite_parcela_contextual = max(base * 3, 2000.0)
        limite_restante_contextual = max(base * 120, 50000.0)

        df = df[df["valor_parcela"] <= limite_parcela_contextual].copy()
        df = df[df["valor_restante"] <= limite_restante_contextual].copy()

    # Padroniza status.
    if "status" in df.columns:
        df["status"] = df["status"].astype(str).str.upper().str.strip()

    # CORREÇÃO PRINCIPAL:
    # remove duplicatas reais antes de qualquer soma.
    df = _deduplicar_compromissos(df)

    return df


# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================

def analisar_compromissos(df_parcelamentos, gasto_total=0, renda_mensal=None):

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
            df[col] = "-" if col in ["status", "compra"] else 0

    df = _limpar_compromissos_absurdos(
        df,
        gasto_total=gasto_total,
        renda_mensal=renda_mensal
    )

    if df is None or df.empty:
        resultado = _df_vazio()
        resultado["qtd_compras"] = len(df_parcelamentos)
        return resultado

    if "status" in df.columns:
        abertos = df[df["status"] == "ABERTO"].copy()
        quitados = df[df["status"] == "QUITADO"].copy()
    else:
        abertos = df[df["valor_restante"] > 0].copy()
        quitados = df[df["valor_restante"] <= 0].copy()

    abertos = abertos[abertos["valor_restante"] > 0].copy()

    # Segurança extra: remove duplicidade também após separar abertos.
    abertos = _deduplicar_compromissos(abertos)

    if abertos.empty:
        resultado = _df_vazio()
        resultado["qtd_compras"] = len(df)
        resultado["qtd_quitados"] = len(quitados)
        return resultado

    valor_restante_total = float(abertos["valor_restante"].sum())
    valor_total_compras = float(abertos["valor_total_compra"].sum())
    impacto_mensal = float(abertos["valor_parcela"].sum())

    base_referencia = renda_mensal if renda_mensal else gasto_total

    impacto_mensal_percentual = (
        impacto_mensal / float(base_referencia) * 100
        if base_referencia and float(base_referencia) > 0
        else 0
    )

    comprometimento_percentual = (
        valor_restante_total / float(gasto_total) * 100
        if gasto_total and float(gasto_total) > 0
        else 0
    )

    maior_saldo = abertos.sort_values("valor_restante", ascending=False).iloc[0]
    maior_compromisso = str(_valor_seguro(maior_saldo, "compra", "-"))
    maior_valor_restante = float(_valor_seguro(maior_saldo, "valor_restante", 0))
    maior_valor_parcela = float(_valor_seguro(maior_saldo, "valor_parcela", 0))
    maior_parcelas_abertas = int(_valor_seguro(maior_saldo, "parcelas_abertas", 0))

    maior_parcela = abertos.sort_values("valor_parcela", ascending=False).iloc[0]
    maior_parcela_compra = str(_valor_seguro(maior_parcela, "compra", "-"))
    maior_parcela_valor = float(_valor_seguro(maior_parcela, "valor_parcela", 0))
    maior_parcela_restantes = int(_valor_seguro(maior_parcela, "parcelas_abertas", 0))

    meses_estimados_comprometidos = int(abertos["parcelas_abertas"].max())

    if impacto_mensal_percentual <= 10:
        nivel_risco = "🟢 Saudável"
        classificacao = "SAUDÁVEL"
        pode_assumir = True
        acao = "Seu nível de parcelas está controlado. Evite parcelar consumo recorrente."

    elif impacto_mensal_percentual <= 20:
        nivel_risco = "🟡 Atenção"
        classificacao = "ATENÇÃO"
        pode_assumir = False
        acao = "Evite novas parcelas até reduzir parte dos compromissos atuais."

    elif impacto_mensal_percentual <= 30:
        nivel_risco = "🟠 Alto"
        classificacao = "ALTO"
        pode_assumir = False
        acao = "Priorize reduzir os maiores compromissos antes de assumir nova compra parcelada."

    else:
        nivel_risco = "🔴 Crítico"
        classificacao = "CRÍTICO"
        pode_assumir = False
        acao = "Não assuma novas parcelas. Reduza o impacto mensal antes de novas obrigações."

    mensagem = (
        f"Você possui {moeda(valor_restante_total)} em parcelas futuras. "
        f"O impacto mensal estimado é de {moeda(impacto_mensal)}, equivalente a "
        f"{impacto_mensal_percentual:.1f}% da referência analisada."
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


# ============================================================
# TEXTOS
# ============================================================

def gerar_resumo_executivo_compromissos(resultado):
    if not resultado.get("tem_compromissos", False):
        return (
            "Nenhuma compra parcelada em aberto foi identificada. "
            "Seu nível de compromissos futuros está saudável."
        )

    return (
        f"Foram identificados {resultado['qtd_abertos']} parcelamentos em aberto. "
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


# ============================================================
# TABELAS TOP
# ============================================================

def gerar_top_compromissos(df_parcelamentos, top=5):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return pd.DataFrame()

    df = _limpar_compromissos_absurdos(df_parcelamentos.copy())

    if df is None or df.empty:
        return pd.DataFrame()

    for col in ["compra", "valor_parcela", "parcelas_abertas", "valor_restante", "valor_total_compra", "status"]:
        if col not in df.columns:
            df[col] = 0 if col not in ["compra", "status"] else "-"

    df = df[df["valor_restante"] > 0].copy()
    df = _deduplicar_compromissos(df)

    if df.empty:
        return pd.DataFrame()

    return df.sort_values("valor_restante", ascending=False).head(top)[
        ["compra", "valor_parcela", "parcelas_abertas", "valor_restante", "valor_total_compra", "status"]
    ]


def gerar_top_impacto_mensal(df_parcelamentos, top=5):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return pd.DataFrame()

    df = _limpar_compromissos_absurdos(df_parcelamentos.copy())

    if df is None or df.empty:
        return pd.DataFrame()

    for col in ["compra", "valor_parcela", "parcelas_abertas", "valor_restante", "status"]:
        if col not in df.columns:
            df[col] = 0 if col not in ["compra", "status"] else "-"

    df = df[df["valor_restante"] > 0].copy()
    df = _deduplicar_compromissos(df)

    if df.empty:
        return pd.DataFrame()

    return df.sort_values("valor_parcela", ascending=False).head(top)[
        ["compra", "valor_parcela", "parcelas_abertas", "valor_restante", "status"]
    ]


def gerar_texto_capacidade(resultado):
    return (
        f"O impacto mensal das parcelas é de {moeda(resultado.get('impacto_mensal', 0))}, "
        f"equivalente a {resultado.get('impacto_mensal_percentual', 0):.1f}% da referência analisada. "
        f"{resultado.get('acao', '')}"
    )
