# ============================================================
# parcelamento_engine.py
# ORÇAMENTO INTELIGENTE
# Versão preservada + universal
#
# Mantém a lógica que já lia várias faturas e acrescenta:
# - conversor de valor seguro
# - Caixa/Nubank: 09 DE 10, 06 DE 06, 09/10
# - bloqueio de simulação/oferta de parcelamento da fatura
# - preserva leitura por documento e DataFrame
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

    try:
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
            return float(texto)
        return float(texto)
    except Exception:
        return 0.0


PADRAO_VALOR = re.compile(
    r"R?\$?\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\s*[DC]?",
    re.IGNORECASE
)

PADRAO_NX_DE = re.compile(
    r"(?P<qtd>\d{1,2})\s*[Xx]\s*(?:DE|POR)?\s*R?\$?\s*(?P<valor>[\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
    re.IGNORECASE
)

PADRAO_PARC_EXPLICITA = re.compile(
    r"\b(?:PARC|PARC\.|PARCELA|PARCELADO|COMPRA PARCELADA)\.?\s*"
    r"(?P<atual>\d{1,2})\s*(?:/|DE)\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

PADRAO_DE_CONTEXTUAL = re.compile(
    r"\b(?P<atual>\d{1,2})\s*DE\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

PADRAO_BARRA_CONTEXTUAL = re.compile(
    r"\b(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

PADRAO_NX = re.compile(
    r"\b(?P<total>\d{1,2})\s*X\b",
    re.IGNORECASE
)

PADRAO_EM_NX = re.compile(
    r"\bEM\s*(?P<total>\d{1,2})\s*X\b",
    re.IGNORECASE
)

PADRAO_N_PARCELAS = re.compile(
    r"\b(?P<total>\d{1,2})\s*(?:PARCELAS|PRESTACOES|PRESTAÇÕES)\b",
    re.IGNORECASE
)

PADRAO_DATA_CURTA = re.compile(
    r"\b\d{2}/\d{2}(?:/\d{4})?\b",
    re.IGNORECASE
)

PADRAO_DATA_EXTENSO = re.compile(
    r"\b\d{1,2}\s+DE\s+[A-ZÇ]{3,12}\.?\s+\d{4}\b",
    re.IGNORECASE
)


TERMOS_BLOQUEADOS = [
    "PAGAMENTO", "PIX", "BOLETO", "ESTORNO", "CREDITO", "CRÉDITO",
    "JUROS", "IOF", "ENCARGOS", "ROTATIVO", "TOTAL DA FATURA",
    "VALOR TOTAL DA FATURA", "DESPESAS DA FATURA", "LIMITE", "VENCIMENTO",
    "PAGAMENTO MINIMO", "PAGAMENTO MÍNIMO", "PAGAMENTO TOTAL", "SALDO", "CET",
    "MULTA", "MORA", "TARIFA"
]

TERMOS_OFERTA_PARCELAMENTO = [
    "PARCELAMENTO DE FATURA", "OPCOES PARA PAGAMENTO", "OPÇÕES PARA PAGAMENTO",
    "TOTAL DAS PARCELAS", "TOTAL DA FATURA", "TOTAL DEVIDO", "JUROS EFETIVOS",
    "CET", "IOF", "MINIMO", "MÍNIMO", "ROTATIVO", "CONTRATACAO", "CONTRATAÇÃO",
    "SIMULAR", "SIMULE", "VOCE TAMBEM PODE SIMULAR", "VOCÊ TAMBÉM PODE SIMULAR",
    "PARCELE A SUA FATURA", "ESCOLHA UMA DAS OPCOES", "ESCOLHA UMA DAS OPÇÕES"
]

CABECALHOS = [
    "DATA DESCRICAO CIDADE PAIS VALOR",
    "DATA DESCRIÇÃO CIDADE PAÍS VALOR",
    "DATA DESCRICAO VALOR",
    "DATA DESCRIÇÃO VALOR",
    "QTD PARCELAS",
    "PARCELAS 1A PARCELA",
    "PARCELAS 1ª PARCELA",
    "JUROS EFETIVOS",
    "VALOR ORIGINAL COTACAO",
    "VALOR ORIGINAL COTAÇÃO",
]


def contem_bloqueado(texto):
    texto = normalizar_texto(texto)
    return any(normalizar_texto(t) in texto for t in TERMOS_BLOQUEADOS)


def contem_oferta_parcelamento(texto):
    texto = normalizar_texto(texto)
    return any(normalizar_texto(t) in texto for t in TERMOS_OFERTA_PARCELAMENTO)


def contem_cabecalho(texto):
    texto = normalizar_texto(texto)
    return any(normalizar_texto(t) in texto for t in CABECALHOS)


def linha_administrativa(texto):
    texto = normalizar_texto(texto)
    if not texto:
        return True
    if contem_cabecalho(texto):
        return True
    if contem_oferta_parcelamento(texto):
        return True
    if contem_bloqueado(texto):
        return True
    return False


def limpar_compra(texto):
    texto = normalizar_texto(texto)
    texto = PADRAO_NX_DE.sub(" ", texto)
    texto = PADRAO_PARC_EXPLICITA.sub(" ", texto)
    texto = PADRAO_DE_CONTEXTUAL.sub(" ", texto)
    texto = PADRAO_BARRA_CONTEXTUAL.sub(" ", texto)
    texto = PADRAO_NX.sub(" ", texto)
    texto = PADRAO_EM_NX.sub(" ", texto)
    texto = PADRAO_N_PARCELAS.sub(" ", texto)
    texto = PADRAO_VALOR.sub(" ", texto)
    texto = PADRAO_DATA_EXTENSO.sub(" ", texto)
    texto = PADRAO_DATA_CURTA.sub(" ", texto)

    texto = re.sub(r"\bCARTAO\s+\d+\b", " ", texto)
    texto = re.sub(r"\bCARTÃO\s+\d+\b", " ", texto)
    texto = re.sub(r"\bCOMPRAS PARCELADAS\b", " ", texto)
    texto = re.sub(r"\bCREDITO/DEBITO\b", " ", texto)
    texto = re.sub(r"\bCRÉDITO/DÉBITO\b", " ", texto)
    texto = re.sub(r"[*|]+", " ", texto)
    texto = re.sub(r"\(\s*\)", " ", texto)
    texto = re.sub(r"[-–—]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" -")


def compra_valida(compra):
    compra = normalizar_texto(compra)
    if not compra:
        return False
    if len(compra) < 3:
        return False
    if len(compra) > 100:
        return False
    if linha_administrativa(compra):
        return False
    if not re.search(r"[A-Z]", compra):
        return False
    return True


def encontrar_coluna_descricao(df):
    for col in [
        "descricao_original", "descricao_normalizada", "merchant",
        "descricao", "estabelecimento", "compra", "texto", "lancamento",
    ]:
        if col in df.columns:
            return col

    for col in df.columns:
        if df[col].dtype == "object":
            return col

    return None


def encontrar_coluna_valor(df):
    for col in ["valor", "valor_parcela", "valor_total", "total", "amount", "gasto"]:
        if col in df.columns:
            return col

    numericas = df.select_dtypes(include="number").columns.tolist()
    return numericas[0] if numericas else None


def extrair_valor_evidencia(texto):
    valores = [converter_valor(v) for v in PADRAO_VALOR.findall(str(texto or ""))]
    valores = [v for v in valores if v > 0]
    if not valores:
        return 0.0
    return valores[-1]


def corrigir_valor(valor_atual, evidencia=""):
    valor_evidencia = extrair_valor_evidencia(evidencia)
    if valor_evidencia > 0:
        return round(valor_evidencia, 2)

    valor = converter_valor(valor_atual)
    if valor <= 0:
        return 0.0

    if valor >= 1000 and float(valor).is_integer():
        return round(valor / 100, 2)

    if 100 <= valor < 1000 and float(valor).is_integer():
        return round(valor / 10, 2)

    return round(valor, 2)


def chave_compra(compra):
    c = limpar_compra(compra)
    c = normalizar_texto(c)
    c = re.sub(r"[^A-Z0-9 ]", " ", c)

    substituicoes = {
        "MERC PAGO": "MERCADO PAGO",
        "MERCPAGO": "MERCADO PAGO",
        "MERCADOPAGO": "MERCADO PAGO",
        "MP ": "MERCADO PAGO ",
        "PAG SEGURO": "PAGSEGURO",
        "GET NET": "GETNET",
        "SAFRA PAY": "SAFRAPAY",
        "ADIQPLU": "ADIQ",
        "ADIQPAY": "ADIQ",
        "BLU INSTITUICAO DE PAG": "BLU",
        "BLU INSTITUICAO": "BLU",
    }

    for antigo, novo in substituicoes.items():
        c = c.replace(antigo, novo)

    c = re.sub(r"\s+", " ", c).strip()
    return c


def extrair_parcela_texto(texto):
    texto = normalizar_texto(texto)

    if linha_administrativa(texto):
        return 0, 0, 0.0, ""

    m = PADRAO_PARC_EXPLICITA.search(texto)
    if m:
        atual = int(m.group("atual"))
        total = int(m.group("total"))
        if 1 <= atual <= total <= MAX_TOTAL_PARCELAS:
            return atual, total, 0.0, "PARCELA_EXPLICITA"

    m = PADRAO_NX_DE.search(texto)
    if m:
        total = int(m.group("qtd"))
        valor_parcela = converter_valor(m.group("valor"))
        if 1 <= total <= MAX_TOTAL_PARCELAS and valor_parcela > 0:
            return 0, total, valor_parcela, "NX_DE_VALOR"

    m = PADRAO_EM_NX.search(texto)
    if m:
        total = int(m.group("total"))
        if 1 <= total <= MAX_TOTAL_PARCELAS:
            return 0, total, 0.0, "EM_NX"

    m = PADRAO_NX.search(texto)
    if m:
        total = int(m.group("total"))
        if 1 <= total <= MAX_TOTAL_PARCELAS:
            return 0, total, 0.0, "NX"

    m = PADRAO_DE_CONTEXTUAL.search(texto)
    if m:
        atual = int(m.group("atual"))
        total = int(m.group("total"))
        if 1 <= atual <= total <= MAX_TOTAL_PARCELAS:
            return atual, total, 0.0, "DE_CONTEXTUAL"

    m = PADRAO_BARRA_CONTEXTUAL.search(texto)
    if m and PADRAO_VALOR.search(texto):
        atual = int(m.group("atual"))
        total = int(m.group("total"))
        if 1 <= atual <= total <= MAX_TOTAL_PARCELAS:
            return atual, total, 0.0, "BARRA_CONTEXTUAL"

    m = PADRAO_N_PARCELAS.search(texto)
    if m:
        total = int(m.group("total"))
        if 1 <= total <= MAX_TOTAL_PARCELAS:
            return 0, total, 0.0, "N_PARCELAS"

    return 0, 0, 0.0, ""


def extrair_parcelamentos_documento(texto, arquivo=""):
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    registros = []
    contexto = []
    dentro_compras_parceladas = False

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if linha_norm.startswith("--- PAGINA"):
            contexto = []
            dentro_compras_parceladas = False
            continue

        if "COMPRAS PARCELADAS" in linha_norm or "DESPESAS A VENCER" in linha_norm:
            dentro_compras_parceladas = True
            contexto = []
            continue

        if (
            "TOTAL COMPRAS PARCELADAS" in linha_norm
            or "TOTAL FINAL" in linha_norm
            or "VALOR TOTAL DESTA FATURA" in linha_norm
            or "LEGENDA" in linha_norm
            or "OPERACAO CONTRATADA" in linha_norm
            or "OPERAÇÃO CONTRATADA" in linha_norm
        ):
            contexto = []
            dentro_compras_parceladas = False
            continue

        if linha_administrativa(linha_norm):
            contexto = []
            continue

        atual, total, valor_detectado, tipo = extrair_parcela_texto(linha_norm)

        if total > 0:
            valor_linha = extrair_valor_evidencia(linha_norm)

            if valor_detectado > 0:
                valor_parcela = valor_detectado
            else:
                valor_parcela = valor_linha

            if valor_parcela <= 0:
                continue

            compra_linha = limpar_compra(linha_norm)
            compra_contexto = limpar_compra(" ".join(contexto[-3:]))
            compra = compra_linha if compra_valida(compra_linha) else compra_contexto

            if compra_valida(compra) and valor_parcela > 0:
                registros.append({
                    "arquivo_fatura": arquivo,
                    "compra": compra,
                    "compra_key": chave_compra(compra),
                    "categoria": "Outros",
                    "ultima_parcela": atual,
                    "total_parcelas": total,
                    "valor_parcela": valor_parcela,
                    "descricao_detectada": linha,
                    "tipo_detectado": f"DOC_{tipo}",
                    "valor_total_informado": total * valor_parcela,
                    "confianca_extracao": 0,
                    "prioridade_origem": 1,
                })

            contexto = []
            continue

        if compra_valida(linha_norm):
            contexto.append(linha_norm)
            contexto = contexto[-3:]

    return registros


def extrair_parcelamentos_df(df_base):
    if df_base is None or df_base.empty:
        return []

    coluna_desc = encontrar_coluna_descricao(df_base)
    coluna_valor = encontrar_coluna_valor(df_base)

    if coluna_desc is None:
        return []

    registros = []

    for _, linha in df_base.iterrows():
        descricao = str(linha.get(coluna_desc, ""))
        descricao_original = str(linha.get("descricao_original", descricao))
        linha_original_pdf = str(linha.get("linha_original_pdf", descricao_original))
        evidencia = linha_original_pdf or descricao_original or descricao

        if linha_administrativa(evidencia):
            continue

        valor_base = linha.get("valor_parcela", linha.get(coluna_valor, 0) if coluna_valor else 0)
        valor = corrigir_valor(valor_base, evidencia)

        categoria = linha.get("categoria", "Outros")
        arquivo = linha.get("arquivo_fatura", "")

        parcelado = bool(linha.get("parcelado", False))
        parcela_atual = int(pd.to_numeric(linha.get("parcela_atual", 0), errors="coerce") or 0)
        total_parcelas = int(pd.to_numeric(linha.get("total_parcelas", 0), errors="coerce") or 0)
        tipo_parcela = str(linha.get("tipo_parcela", ""))
        confianca = int(pd.to_numeric(linha.get("confianca_extracao", 0), errors="coerce") or 0)

        if parcelado and total_parcelas > 0:
            atual = parcela_atual
            total = total_parcelas
            tipo = f"TX_ENGINE_{tipo_parcela or 'PARCELADO'}"
        else:
            atual, total, valor_detectado, tipo_extraido = extrair_parcela_texto(evidencia)
            tipo = f"DF_{tipo_extraido}"
            if valor_detectado > 0:
                valor = valor_detectado

        if total <= 0:
            continue

        if not (0 <= atual <= total <= MAX_TOTAL_PARCELAS):
            continue

        if valor <= 0 or valor > MAX_VALOR_PARCELA:
            continue

        compra = limpar_compra(descricao)
        if not compra_valida(compra):
            compra = limpar_compra(descricao_original)
        if not compra_valida(compra):
            compra = limpar_compra(evidencia)
        if not compra_valida(compra):
            continue

        registros.append({
            "arquivo_fatura": arquivo,
            "compra": compra,
            "compra_key": chave_compra(compra),
            "categoria": categoria,
            "ultima_parcela": atual,
            "total_parcelas": total,
            "valor_parcela": valor,
            "descricao_detectada": evidencia,
            "tipo_detectado": tipo,
            "valor_total_informado": total * valor,
            "confianca_extracao": confianca,
            "prioridade_origem": 2 if str(tipo).startswith("TX_ENGINE") else 1,
        })

    return registros


def consolidar_parcelamentos(registros):
    colunas = [
        "arquivo_fatura", "compra", "categoria", "ultima_parcela",
        "total_parcelas", "parcelas_pagas", "parcelas_abertas",
        "valor_parcela", "valor_total_compra", "valor_pago",
        "valor_restante", "status", "tipo_detectado",
        "descricao_detectada", "classificacao_validacao", "confianca_extracao"
    ]

    if not registros:
        return pd.DataFrame(columns=colunas)

    base = pd.DataFrame(registros)

    if base.empty:
        return pd.DataFrame(columns=colunas)

    if "compra_key" not in base.columns:
        base["compra_key"] = base["compra"].apply(chave_compra)

    base["compra_key"] = base["compra_key"].fillna(base["compra"].apply(chave_compra))
    base["valor_parcela"] = pd.to_numeric(base["valor_parcela"], errors="coerce").fillna(0)
    base["total_parcelas"] = pd.to_numeric(base["total_parcelas"], errors="coerce").fillna(0).astype(int)
    base["ultima_parcela"] = pd.to_numeric(base["ultima_parcela"], errors="coerce").fillna(0).astype(int)
    base["prioridade_origem"] = pd.to_numeric(base.get("prioridade_origem", 1), errors="coerce").fillna(1).astype(int)
    base["confianca_extracao"] = pd.to_numeric(base.get("confianca_extracao", 0), errors="coerce").fillna(0).astype(int)

    base = base[base["valor_parcela"] > 0]
    base = base[base["valor_parcela"] <= MAX_VALOR_PARCELA]
    base = base[base["total_parcelas"] > 0]
    base = base[base["total_parcelas"] <= MAX_TOTAL_PARCELAS]
    base = base[base["ultima_parcela"] <= base["total_parcelas"]]
    base = base[base["compra_key"].astype(str).str.len() >= 3]

    if base.empty:
        return pd.DataFrame(columns=colunas)

    consolidados = []

    for (compra_key, total_parcelas), grupo in base.groupby(["compra_key", "total_parcelas"], dropna=False):
        grupo = grupo.copy()

        if grupo["tipo_detectado"].astype(str).str.contains("TX_ENGINE", na=False).any():
            grupo = grupo[grupo["tipo_detectado"].astype(str).str.contains("TX_ENGINE", na=False)].copy()

        grupo = grupo.sort_values(
            ["prioridade_origem", "confianca_extracao"],
            ascending=[False, False]
        )

        grupo = grupo.drop_duplicates(
            subset=["compra_key", "total_parcelas", "ultima_parcela"],
            keep="first"
        )

        if grupo.empty:
            continue

        valores = grupo["valor_parcela"].tolist()

        if len(valores) == 1:
            valor_parcela = float(valores[0])
        else:
            max_v = max(valores)
            min_v = min(valores)
            if max_v - min_v <= TOLERANCIA_VALOR:
                valor_parcela = float(pd.Series(valores).median())
            else:
                valor_parcela = float(grupo.iloc[0]["valor_parcela"])

        total = int(total_parcelas)
        ultima = int(grupo["ultima_parcela"].max())

        parcelas_pagas = ultima
        parcelas_abertas = max(total - ultima, 0)
        valor_pago = parcelas_pagas * valor_parcela
        valor_restante = parcelas_abertas * valor_parcela
        valor_total_compra = total * valor_parcela

        status = "QUITADO" if parcelas_abertas == 0 else "ABERTO"
        melhor = grupo.iloc[0]
        tipos = " | ".join(grupo["tipo_detectado"].astype(str).unique())
        descricoes = " | ".join(grupo["descricao_detectada"].astype(str).unique()[:10])
        confianca = int(grupo["confianca_extracao"].max())

        if status == "QUITADO":
            classificacao = "QUITADO"
        elif "TX_ENGINE" in tipos or len(grupo) >= 2 or ultima >= 2:
            classificacao = "CONFIRMADO"
        else:
            classificacao = "CONFIRMADO_INICIAL"

        consolidados.append({
            "arquivo_fatura": melhor.get("arquivo_fatura", ""),
            "compra": melhor.get("compra", compra_key),
            "categoria": melhor.get("categoria", "Outros"),
            "ultima_parcela": ultima,
            "total_parcelas": total,
            "parcelas_pagas": parcelas_pagas,
            "parcelas_abertas": parcelas_abertas,
            "valor_parcela": round(valor_parcela, 2),
            "valor_total_compra": round(valor_total_compra, 2),
            "valor_pago": round(valor_pago, 2),
            "valor_restante": round(valor_restante, 2),
            "status": status,
            "tipo_detectado": tipos,
            "descricao_detectada": descricoes,
            "classificacao_validacao": classificacao,
            "confianca_extracao": confianca,
        })

    resultado = pd.DataFrame(consolidados, columns=colunas)

    if resultado.empty:
        return resultado

    resultado = resultado.sort_values(
        ["status", "valor_restante"],
        ascending=[True, False]
    ).reset_index(drop=True)

    return resultado


def associar_categoria(df_parcelamentos, df_base):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return df_parcelamentos

    if df_base is None or df_base.empty:
        return df_parcelamentos

    if "categoria" not in df_base.columns:
        return df_parcelamentos

    coluna_desc = encontrar_coluna_descricao(df_base)

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
    if isinstance(documentos, pd.DataFrame) and df_base is None:
        df_base = documentos
        documentos = None

    registros = []

    if isinstance(documentos, list):
        for doc in documentos:
            registros.extend(
                extrair_parcelamentos_documento(
                    texto=doc.get("texto", ""),
                    arquivo=doc.get("arquivo", "")
                )
            )

    registros.extend(extrair_parcelamentos_df(df_base))

    df = consolidar_parcelamentos(registros)
    df = associar_categoria(df, df_base)

    return df


def resumo_parcelamentos(df_parcelamentos):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return {
            "parcelamentos": 0,
            "abertos": 0,
            "quitados": 0,
            "valor_restante": 0.0,
            "valor_total_compras": 0.0,
            "maior_compromisso": 0.0,
        }

    abertos = df_parcelamentos[df_parcelamentos["status"] == "ABERTO"]
    quitados = df_parcelamentos[df_parcelamentos["status"] == "QUITADO"]

    return {
        "parcelamentos": int(len(df_parcelamentos)),
        "abertos": int(len(abertos)),
        "quitados": int(len(quitados)),
        "valor_restante": float(abertos["valor_restante"].sum()) if not abertos.empty else 0.0,
        "valor_total_compras": float(abertos["valor_total_compra"].sum()) if not abertos.empty else 0.0,
        "maior_compromisso": float(abertos["valor_restante"].max()) if not abertos.empty else 0.0,
    }
