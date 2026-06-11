# ============================================================
# parcelamento_engine.py
# ORÇAMENTO INTELIGENTE
# Versão blindada e compatível com o app
#
# Objetivo:
# - Ler somente compras parceladas reais
# - Bloquear parcelamento de fatura, CET, IOF, rotativo e simulações
# - Preservar compatibilidade com app.py:
#   processar_parcelamentos(documentos=None, df_base=None)
# - Preservar colunas esperadas por compromissos_engine/dashboard
# ============================================================

import re
import pandas as pd
import unicodedata


TOLERANCIA_VALOR = 0.15
MAX_TOTAL_PARCELAS = 60
MAX_VALOR_PARCELA = 30000.0


def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = texto.replace("ª", "A")
    texto = texto.replace("º", "O")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def converter_valor(valor):
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
    texto = re.sub(r"[DCdc]$", "", texto)

    try:
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
            return float(texto)
        return float(texto)
    except Exception:
        return 0.0


PADRAO_VALOR = re.compile(
    r"R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\s*[DC]?",
    re.IGNORECASE
)

PADRAO_DATA_CURTA = re.compile(
    r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
    re.IGNORECASE
)

PADRAO_DATA_EXTENSO = re.compile(
    r"\b\d{1,2}\s+DE\s+[A-ZÇ]{3,12}\.?\s+\d{4}\b",
    re.IGNORECASE
)

PADRAO_PARCELA_DE = re.compile(
    r"\b(?P<atual>\d{1,2})\s+DE\s+(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

PADRAO_PARCELA_BARRA = re.compile(
    r"\b(?:PARCELA\s*)?(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)


TERMOS_ADMINISTRATIVOS = [
    "VALOR TOTAL", "TOTAL DA FATURA", "TOTAL A PAGAR", "TOTAL FINAL",
    "TOTAL COMPRAS", "PAGAMENTO", "OBRIGADO PELO PAGAMENTO",
    "CREDITO", "CRÉDITO", "AJUSTE", "ESTORNO",
    "LIMITE", "VENCIMENTO", "VALOR DO DOCUMENTO",
    "ROTATIVO", "ATRASO", "IOF", "CET", "JUROS", "MULTA", "MORA",
    "PARCELAMENTO DE FATURA", "PARCELE A SUA FATURA",
    "OPCOES PARA PAGAMENTO", "OPÇÕES PARA PAGAMENTO",
    "QTD PARCELAS", "1A PARCELA", "1 PARCELA", "DEMAIS PARCELAS",
    "JUROS EFETIVOS", "TOTAL DAS PARCELAS", "TOTAL DEVIDO",
    "AO CONTRATAR", "SIMULAR", "ESCOLHA UMA",
    "VALOR ORIGINAL", "COTACAO", "COTAÇÃO",
    "DATA DESCRICAO", "DATA DESCRIÇÃO", "CIDADE/PAIS", "CIDADE/PAÍS",
    "CREDITO/DEBITO", "CRÉDITO/DÉBITO",
    "LEGENDA", "APP CARTOES", "APP CARTÕES",
    "CENTRAL DE ATENDIMENTO", "INFORMACOES COMPLEMENTARES",
    "INFORMAÇÕES COMPLEMENTARES", "OPERACAO CONTRATADA", "OPERAÇÃO CONTRATADA",
    "SALDO CREDITO ROTATIVO", "SALDO CRÉDITO ROTATIVO",
]


def linha_administrativa(linha):
    t = normalizar_texto(linha)

    if not t:
        return True

    if any(term in t for term in TERMOS_ADMINISTRATIVOS):
        return True

    if "%" in t:
        return True

    if re.search(r"\b\d{1,2}X\s+R\$", t):
        return True

    if len(re.findall(r"R\$", t)) >= 2:
        return True

    return False


def limpar_compra(texto):
    texto = normalizar_texto(texto)

    texto = PADRAO_DATA_EXTENSO.sub(" ", texto)
    texto = PADRAO_DATA_CURTA.sub(" ", texto)
    texto = PADRAO_VALOR.sub(" ", texto)
    texto = PADRAO_PARCELA_DE.sub(" ", texto)
    texto = PADRAO_PARCELA_BARRA.sub(" ", texto)

    texto = re.sub(r"\bPARCELA\b", " ", texto)
    texto = re.sub(r"\bCARTAO\s+\d+\b", " ", texto)
    texto = re.sub(r"\bCARTÃO\s+\d+\b", " ", texto)
    texto = re.sub(r"\bCOMPRAS PARCELADAS\b", " ", texto)
    texto = re.sub(r"[*•●|]+", " ", texto)
    texto = re.sub(r"[-–—]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip(" -")


def chave_compra(texto):
    texto = limpar_compra(texto)
    texto = normalizar_texto(texto)
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)

    substituicoes = {
        "PRIVALIA BRA PRIV": "PRIVALIA",
        "PG PRIVALIA PRIV": "PRIVALIA",
        "URBAN URBAN HELMETS": "URBAN HELMETS",
        "VINDI LOJAVIRUS41": "LOJAVIRUS41",
        "VINDI LOJA VIRUS41": "LOJAVIRUS41",
        "EBN SPOTIFY": "SPOTIFY",
    }

    for antigo, novo in substituicoes.items():
        texto = texto.replace(antigo, novo)

    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def compra_valida(compra):
    t = normalizar_texto(compra)

    if len(t) < 3 or len(t) > 100:
        return False

    if linha_administrativa(t):
        return False

    if "%" in t or "R$" in t:
        return False

    if not re.search(r"[A-Z]", t):
        return False

    return True


def extrair_parcela_texto(linha):
    t = normalizar_texto(linha)

    m = PADRAO_PARCELA_DE.search(t)
    if m:
        atual = int(m.group("atual"))
        total = int(m.group("total"))
        if 1 <= atual <= total <= MAX_TOTAL_PARCELAS:
            return atual, total, "DE"

    m = PADRAO_PARCELA_BARRA.search(t)
    if m:
        atual = int(m.group("atual"))
        total = int(m.group("total"))
        if 1 <= atual <= total <= MAX_TOTAL_PARCELAS:
            return atual, total, "BARRA"

    return 0, 0, ""


def extrair_valor_linha(linha):
    valores = [converter_valor(v) for v in PADRAO_VALOR.findall(str(linha or ""))]
    valores = [v for v in valores if v > 0]

    if not valores:
        return 0.0

    return float(valores[-1])


def _df_colunas():
    return [
        "arquivo_fatura",
        "compra",
        "compra_key",
        "categoria",
        "ultima_parcela",
        "total_parcelas",
        "parcelas_pagas",
        "parcelas_abertas",
        "valor_parcela",
        "valor_total_compra",
        "valor_pago",
        "valor_restante",
        "status",
        "tipo_detectado",
        "descricao_detectada",
        "classificacao_validacao",
        "confianca_extracao",
    ]


def extrair_parcelamentos_documento(texto, arquivo=""):
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    registros = []

    dentro_compras_parceladas = False

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if "COMPRAS PARCELADAS" in linha_norm:
            dentro_compras_parceladas = True
            continue

        if any(fim in linha_norm for fim in [
            "TOTAL COMPRAS PARCELADAS",
            "OUTROS (",
            "VALOR TOTAL DESTA FATURA",
            "TOTAL FINAL",
            "LEGENDA",
            "OPERACAO CONTRATADA",
            "OPERAÇÃO CONTRATADA",
            "APP CARTOES",
            "APP CARTÕES",
            "COMPRAS (",
        ]):
            dentro_compras_parceladas = False
            continue

        if not dentro_compras_parceladas:
            continue

        if linha_administrativa(linha_norm):
            continue

        atual, total, tipo = extrair_parcela_texto(linha_norm)

        if total <= 0:
            continue

        valor_parcela = extrair_valor_linha(linha_norm)

        if valor_parcela <= 0 or valor_parcela > MAX_VALOR_PARCELA:
            continue

        compra = limpar_compra(linha_norm)

        if not compra_valida(compra):
            continue

        parcelas_pagas = atual
        parcelas_abertas = max(total - atual, 0)
        valor_pago = parcelas_pagas * valor_parcela
        valor_restante = parcelas_abertas * valor_parcela
        valor_total_compra = total * valor_parcela

        registros.append({
            "arquivo_fatura": arquivo,
            "compra": compra,
            "compra_key": chave_compra(compra),
            "categoria": "Outros",
            "ultima_parcela": int(atual),
            "total_parcelas": int(total),
            "parcelas_pagas": int(parcelas_pagas),
            "parcelas_abertas": int(parcelas_abertas),
            "valor_parcela": float(valor_parcela),
            "valor_total_compra": float(valor_total_compra),
            "valor_pago": float(valor_pago),
            "valor_restante": float(valor_restante),
            "status": "ABERTO" if parcelas_abertas > 0 else "QUITADO",
            "tipo_detectado": f"DOC_{tipo}",
            "descricao_detectada": linha,
            "classificacao_validacao": "CONFIRMADO" if parcelas_abertas > 0 else "QUITADO",
            "confianca_extracao": 90,
        })

    return registros


def associar_categoria(df_parcelamentos, df_base):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return df_parcelamentos

    if df_base is None or df_base.empty:
        return df_parcelamentos

    if "categoria" not in df_base.columns:
        return df_parcelamentos

    coluna_desc = None
    for col in ["descricao_original", "descricao_normalizada", "merchant", "compra"]:
        if col in df_base.columns:
            coluna_desc = col
            break

    if coluna_desc is None:
        return df_parcelamentos

    base = df_base.copy()
    base["_busca"] = base[coluna_desc].apply(chave_compra)

    for idx, row in df_parcelamentos.iterrows():
        compra = chave_compra(row.get("compra", ""))
        if not compra:
            continue

        match = base[base["_busca"].str.contains(compra[:10], regex=False, na=False)]

        if not match.empty:
            df_parcelamentos.at[idx, "categoria"] = match.iloc[0].get("categoria", "Outros")

    return df_parcelamentos


def processar_parcelamentos(documentos=None, df_base=None):
    """
    Compatível com:
    processar_parcelamentos(documentos=documentos, df_base=df_base)
    processar_parcelamentos(documentos)
    processar_parcelamentos(df_base)
    """

    if isinstance(documentos, pd.DataFrame) and df_base is None:
        df_base = documentos
        documentos = None

    todos = []

    if isinstance(documentos, list):
        for doc in documentos:
            if not isinstance(doc, dict):
                continue

            todos.extend(
                extrair_parcelamentos_documento(
                    texto=doc.get("texto", ""),
                    arquivo=doc.get("arquivo", "")
                )
            )

    colunas = _df_colunas()
    df = pd.DataFrame(todos, columns=colunas)

    if df.empty:
        return pd.DataFrame(columns=colunas)

    for col in [
        "ultima_parcela",
        "total_parcelas",
        "parcelas_pagas",
        "parcelas_abertas",
        "valor_parcela",
        "valor_total_compra",
        "valor_pago",
        "valor_restante",
        "confianca_extracao",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df[df["valor_parcela"] > 0].copy()
    df = df[df["valor_parcela"] <= MAX_VALOR_PARCELA].copy()
    df = df[df["total_parcelas"] > 0].copy()
    df = df[df["total_parcelas"] <= MAX_TOTAL_PARCELAS].copy()
    df = df[df["ultima_parcela"] <= df["total_parcelas"]].copy()

    df = df.drop_duplicates(
        subset=[
            "arquivo_fatura",
            "compra_key",
            "ultima_parcela",
            "total_parcelas",
            "valor_parcela",
        ],
        keep="first"
    )

    df["_valor_key"] = df["valor_parcela"].round(2)

    df = df.sort_values(
        ["ultima_parcela", "confianca_extracao"],
        ascending=[False, False]
    )

    df = df.drop_duplicates(
        subset=[
            "compra_key",
            "total_parcelas",
            "_valor_key",
        ],
        keep="first"
    )

    df = df.drop(columns=["_valor_key"], errors="ignore")

    df["parcelas_pagas"] = df["ultima_parcela"].astype(int)
    df["parcelas_abertas"] = (df["total_parcelas"] - df["ultima_parcela"]).clip(lower=0).astype(int)
    df["valor_pago"] = df["parcelas_pagas"] * df["valor_parcela"]
    df["valor_restante"] = df["parcelas_abertas"] * df["valor_parcela"]
    df["valor_total_compra"] = df["total_parcelas"] * df["valor_parcela"]
    df["status"] = df["parcelas_abertas"].apply(lambda x: "ABERTO" if x > 0 else "QUITADO")
    df["classificacao_validacao"] = df["status"].apply(lambda x: "CONFIRMADO" if x == "ABERTO" else "QUITADO")

    df = associar_categoria(df, df_base)

    df = df.sort_values(
        ["valor_restante", "valor_parcela"],
        ascending=False
    ).reset_index(drop=True)

    return df[colunas]


def resumo_parcelamentos(df):
    vazio = {
        "parcelamentos": 0,
        "abertos": 0,
        "quitados": 0,
        "valor_restante": 0.0,
        "valor_total_compras": 0.0,
        "maior_compromisso": 0.0,
        "quantidade": 0,
        "valor_futuro": 0.0,
        "impacto_mensal": 0.0,
        "maior_parcela": 0.0,
        "maior_compra": "-",
    }

    if df is None or df.empty or "status" not in df.columns:
        return vazio

    abertos = df[df["status"] == "ABERTO"].copy()
    quitados = df[df["status"] == "QUITADO"].copy()

    if abertos.empty:
        resultado = vazio.copy()
        resultado["parcelamentos"] = int(len(df))
        resultado["quitados"] = int(len(quitados))
        return resultado

    maior = abertos.sort_values("valor_parcela", ascending=False).iloc[0]

    valor_restante = float(abertos["valor_restante"].sum())
    valor_total_compras = float(abertos["valor_total_compra"].sum())
    impacto_mensal = float(abertos["valor_parcela"].sum())

    return {
        "parcelamentos": int(len(df)),
        "abertos": int(len(abertos)),
        "quitados": int(len(quitados)),
        "valor_restante": valor_restante,
        "valor_total_compras": valor_total_compras,
        "maior_compromisso": float(abertos["valor_restante"].max()),
        "quantidade": int(len(abertos)),
        "valor_futuro": valor_restante,
        "impacto_mensal": impacto_mensal,
        "maior_parcela": float(maior["valor_parcela"]),
        "maior_compra": str(maior["compra"]),
    }
