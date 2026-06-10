# ============================================================
# parcelamento_engine.py
# ORÇAMENTO INTELIGENTE
# Versão genérica — saneador de parcelamentos sem quebrar leitura de gastos
#
# Use junto com o transaction_engine.py que já lia os gastos corretamente.
#
# O que este arquivo faz:
# - lê parcelamentos vindos do transaction_engine.py
# - corrige valores inflados: 12255 -> 122,55 / 2917 -> 291,70 / 16995 -> 169,95
# - usa o valor real quando aparece em "R$ 122,55" na linha original
# - remove textos administrativos de banco
# - remove duplicidade TX_ENGINE x DOC_ENGINE
# - consolida a mesma compra em uma única linha
# - não contém regra específica para suas faturas
# ============================================================

import re
import pandas as pd
import unicodedata


TOLERANCIA_VALOR = 0.20
MAX_TOTAL_PARCELAS = 60
MAX_VALOR_PARCELA = 30000.0


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def converter_valor(valor):
    """
    Conversor seguro:
    - 169.95   -> 169.95
    - 169,95   -> 169.95
    - 1.699,95 -> 1699.95
    - R$ 69,90 -> 69.90
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


# ============================================================
# PADRÕES
# ============================================================

PADRAO_VALOR = re.compile(
    r"R?\$?\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
    re.IGNORECASE
)

PADRAO_PARC_EXPLICITA = re.compile(
    r"\b(?:PARC|PARC\.|PARCELA|PARCELADO|COMPRA\s+PARCELADA)\.?\s*"
    r"(?P<atual>\d{1,2})\s*(?:/|DE)\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

PADRAO_NX_DE = re.compile(
    r"\b(?P<qtd>\d{1,2})\s*[Xx]\s*(?:DE|POR)?\s*R?\$?\s*(?P<valor>[\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
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

PADRAO_DATA_NUMERICA = re.compile(r"\b\d{2}/\d{2}(?:/\d{4})?\b")

PADRAO_DATA_EXTENSO = re.compile(
    r"\b\d{1,2}\s+DE\s+[A-ZÇ]{3,12}\.?\s+\d{4}\b",
    re.IGNORECASE
)


TERMOS_ADMINISTRATIVOS = [
    "PAGAMENTO",
    "PIX",
    "BOLETO",
    "ESTORNO",
    "CREDITO",
    "CRÉDITO",
    "JUROS",
    "IOF",
    "ENCARGOS",
    "ROTATIVO",
    "TOTAL DA FATURA",
    "VALOR TOTAL DA FATURA",
    "DESPESAS DA FATURA",
    "LIMITE",
    "VENCIMENTO",
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "PAGAMENTO TOTAL",
    "SALDO",
    "CET",
    "PARCELAMENTO AUTOMATICO",
    "PARCELAMENTO AUTOMÁTICO",
    "PARCELAMENTO E REALIZADO AUTOMATICAMENTE",
    "PARCELAMENTO É REALIZADO AUTOMATICAMENTE",
    "CASO ISTO OCORRA",
    "APLICACAO DE JUROS",
    "APLICAÇÃO DE JUROS",
    "JUROS REMUNERATORIOS",
    "JUROS REMUNERATÓRIOS",
    "CANCELANDO O AGENDAMENTO",
    "DESATIVAR O DEBITO AUTOMATICO",
    "DESATIVAR O DÉBITO AUTOMÁTICO",
]


# ============================================================
# UTILITÁRIOS
# ============================================================

def contem_admin(texto):
    texto = normalizar_texto(texto)
    return any(normalizar_texto(t) in texto for t in TERMOS_ADMINISTRATIVOS)


def extrair_valor_da_evidencia(texto):
    valores = [converter_valor(v) for v in PADRAO_VALOR.findall(str(texto or ""))]
    valores = [v for v in valores if v > 0]

    if not valores:
        return 0.0

    return valores[-1]


def corrigir_valor(valor_atual, evidencia=""):
    """
    Prioridade:
    1. valor escrito na própria linha original em formato monetário;
    2. valor atual se já estiver plausível;
    3. correção de inteiro inflado.
    """
    valor_evidencia = extrair_valor_da_evidencia(evidencia)

    if valor_evidencia > 0:
        return valor_evidencia

    valor = converter_valor(valor_atual)

    if valor <= 0:
        return 0.0

    # 12255 -> 122.55 | 16995 -> 169.95 | 4999 -> 49.99
    if valor >= 1000 and float(valor).is_integer():
        return round(valor / 100, 2)

    # 699 -> 69.90 | 500 -> 50.00 | 710 -> 71.00
    # Só aplica para inteiro sem centavos.
    if 100 <= valor < 1000 and float(valor).is_integer():
        return round(valor / 10, 2)

    return round(valor, 2)


def limpar_compra(texto):
    texto = normalizar_texto(texto)

    texto = PADRAO_DATA_EXTENSO.sub(" ", texto)
    texto = PADRAO_DATA_NUMERICA.sub(" ", texto)
    texto = PADRAO_NX_DE.sub(" ", texto)
    texto = PADRAO_PARC_EXPLICITA.sub(" ", texto)
    texto = PADRAO_NX.sub(" ", texto)
    texto = PADRAO_EM_NX.sub(" ", texto)
    texto = PADRAO_N_PARCELAS.sub(" ", texto)
    texto = PADRAO_VALOR.sub(" ", texto)

    texto = texto.replace("R$", " ")
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

    if contem_admin(compra):
        return False

    if not re.search(r"[A-Z]", compra):
        return False

    return True


def chave_compra(compra):
    c = limpar_compra(compra)
    c = normalizar_texto(c)
    c = re.sub(r"[^A-Z0-9 ]", " ", c)
    c = re.sub(r"\s+", " ", c).strip()

    substituicoes_genericas = {
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

    for antigo, novo in substituicoes_genericas.items():
        c = c.replace(antigo, novo)

    return re.sub(r"\s+", " ", c).strip()


def encontrar_coluna_descricao(df):
    for col in [
        "descricao_normalizada",
        "descricao_original",
        "merchant",
        "descricao",
        "estabelecimento",
        "compra",
        "texto",
        "lancamento",
    ]:
        if col in df.columns:
            return col

    for col in df.columns:
        if df[col].dtype == "object":
            return col

    return None


# ============================================================
# EXTRAÇÃO DE PARCELA EM TEXTO
# ============================================================

def extrair_parcela_texto(texto):
    texto = normalizar_texto(texto)

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

    # não aceita "15 parcelas" isolado em texto administrativo.
    if not contem_admin(texto):
        m = PADRAO_N_PARCELAS.search(texto)
        if m:
            total = int(m.group("total"))

            if 1 <= total <= MAX_TOTAL_PARCELAS:
                return 0, total, 0.0, "N_PARCELAS"

    return 0, 0, 0.0, ""


# ============================================================
# EXTRAÇÃO A PARTIR DO TRANSACTION ENGINE
# ============================================================

def extrair_parcelamentos_transacoes(df_base):
    if df_base is None or df_base.empty:
        return []

    registros = []
    temp = df_base.copy()

    coluna_desc = encontrar_coluna_descricao(temp)

    if coluna_desc is None:
        return []

    for _, linha in temp.iterrows():
        descricao = str(linha.get(coluna_desc, ""))
        descricao_original = str(linha.get("descricao_original", descricao))
        linha_original_pdf = str(linha.get("linha_original_pdf", descricao_original))
        evidencia = linha_original_pdf or descricao_original or descricao

        if contem_admin(evidencia):
            continue

        categoria = linha.get("categoria", "Outros")
        arquivo = linha.get("arquivo_fatura", "")

        parcelado = bool(linha.get("parcelado", False))

        parcela_atual = int(pd.to_numeric(linha.get("parcela_atual", 0), errors="coerce") or 0)
        total_parcelas = int(pd.to_numeric(linha.get("total_parcelas", 0), errors="coerce") or 0)

        tipo_parcela = str(linha.get("tipo_parcela", ""))
        confianca = int(pd.to_numeric(linha.get("confianca_extracao", 0), errors="coerce") or 0)

        valor_lancamento = linha.get("valor", 0)
        valor_parcela_col = linha.get("valor_parcela", 0)

        if parcelado and total_parcelas > 0:
            if parcela_atual < 0 or parcela_atual > total_parcelas:
                continue

            if total_parcelas > MAX_TOTAL_PARCELAS:
                continue

            valor_parcela = corrigir_valor(valor_parcela_col, evidencia)

            if valor_parcela <= 0:
                valor_parcela = corrigir_valor(valor_lancamento, evidencia)

            if valor_parcela <= 0 or valor_parcela > MAX_VALOR_PARCELA:
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
                "ultima_parcela": parcela_atual,
                "total_parcelas": total_parcelas,
                "valor_parcela": valor_parcela,
                "descricao_detectada": evidencia,
                "tipo_detectado": f"TX_ENGINE_{tipo_parcela or 'PARCELADO'}",
                "confianca_extracao": confianca,
                "prioridade_origem": 2,
            })

            continue

        # Fallback interno: só se a própria linha tiver padrão de parcela.
        texto_busca = " ".join([descricao, descricao_original, linha_original_pdf])

        if contem_admin(texto_busca):
            continue

        atual, total, valor_detectado, tipo = extrair_parcela_texto(texto_busca)

        if total <= 0:
            continue

        valor_parcela = valor_detectado if valor_detectado > 0 else corrigir_valor(valor_lancamento, texto_busca)

        if valor_parcela <= 0 or valor_parcela > MAX_VALOR_PARCELA:
            continue

        compra = limpar_compra(texto_busca)

        if not compra_valida(compra):
            continue

        registros.append({
            "arquivo_fatura": arquivo,
            "compra": compra,
            "compra_key": chave_compra(compra),
            "categoria": categoria,
            "ultima_parcela": atual,
            "total_parcelas": total,
            "valor_parcela": valor_parcela,
            "descricao_detectada": evidencia,
            "tipo_detectado": f"DF_{tipo}",
            "confianca_extracao": confianca,
            "prioridade_origem": 1,
        })

    return registros


# ============================================================
# FALLBACK POR DOCUMENTO — CONSERVADOR
# ============================================================

def extrair_parcelamentos_documento(texto, arquivo=""):
    registros = []

    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if contem_admin(linha_norm):
            continue

        m = PADRAO_PARC_EXPLICITA.search(linha_norm)

        if not m:
            continue

        atual = int(m.group("atual"))
        total = int(m.group("total"))

        if not (1 <= atual <= total <= MAX_TOTAL_PARCELAS):
            continue

        valor_parcela = extrair_valor_da_evidencia(linha_norm)

        if valor_parcela <= 0 or valor_parcela > MAX_VALOR_PARCELA:
            continue

        compra = limpar_compra(linha_norm)

        if not compra_valida(compra):
            continue

        registros.append({
            "arquivo_fatura": arquivo,
            "compra": compra,
            "compra_key": chave_compra(compra),
            "categoria": "Outros",
            "ultima_parcela": atual,
            "total_parcelas": total,
            "valor_parcela": valor_parcela,
            "descricao_detectada": linha,
            "tipo_detectado": "DOC_PARCELA_EXPLICITA",
            "confianca_extracao": 0,
            "prioridade_origem": 1,
        })

    return registros


def extrair_parcelamentos_df(df_base):
    return extrair_parcelamentos_transacoes(df_base)


# ============================================================
# CONSOLIDAÇÃO
# ============================================================

def consolidar_parcelamentos(registros):
    colunas = [
        "arquivo_fatura", "compra", "categoria", "ultima_parcela",
        "total_parcelas", "parcelas_pagas", "parcelas_abertas",
        "valor_parcela", "valor_total_compra", "valor_pago",
        "valor_restante", "status", "tipo_detectado",
        "descricao_detectada", "classificacao_validacao",
        "confianca_extracao"
    ]

    if not registros:
        return pd.DataFrame(columns=colunas)

    base = pd.DataFrame(registros)

    if base.empty:
        return pd.DataFrame(columns=colunas)

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

        # TX tem prioridade sobre DOC da mesma compra.
        if grupo["tipo_detectado"].astype(str).str.contains("TX_ENGINE", na=False).any():
            grupo = grupo[grupo["tipo_detectado"].astype(str).str.contains("TX_ENGINE", na=False)].copy()

        grupo = grupo.sort_values(
            ["prioridade_origem", "confianca_extracao"],
            ascending=[False, False]
        )

        # Remove repetição da mesma parcela.
        grupo = grupo.drop_duplicates(
            subset=["compra_key", "total_parcelas", "ultima_parcela"],
            keep="first"
        )

        if grupo.empty:
            continue

        # Valor da parcela:
        # usa mediana dos valores próximos; se houver divergência, usa origem mais confiável.
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
        descricoes = " | ".join(grupo["descricao_detectada"].astype(str).unique()[:8])
        confianca = int(grupo["confianca_extracao"].max())

        if status == "QUITADO":
            classificacao = "QUITADO"
        elif "TX_ENGINE" in tipos or len(grupo) >= 2:
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


# ============================================================
# CATEGORIA
# ============================================================

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
    base["_key"] = base[coluna_desc].apply(chave_compra)

    for idx, row in df_parcelamentos.iterrows():
        key = chave_compra(row.get("compra", ""))

        if not key:
            continue

        match = base[base["_key"].str.contains(key[:12], regex=False, na=False)]

        if not match.empty:
            df_parcelamentos.at[idx, "categoria"] = match.iloc[0].get("categoria", "Outros")

    return df_parcelamentos


# ============================================================
# PROCESSAMENTO PRINCIPAL
# ============================================================

def processar_parcelamentos(documentos=None, df_base=None):
    if isinstance(documentos, pd.DataFrame) and df_base is None:
        df_base = documentos
        documentos = None

    registros = []

    # Principal: usa o que o transaction_engine já extraiu.
    registros.extend(extrair_parcelamentos_transacoes(df_base))

    # Fallback documental só roda se não veio nada estruturado.
    if len(registros) == 0 and isinstance(documentos, list):
        for doc in documentos:
            registros.extend(
                extrair_parcelamentos_documento(
                    texto=doc.get("texto", ""),
                    arquivo=doc.get("arquivo", "")
                )
            )

    df = consolidar_parcelamentos(registros)
    df = associar_categoria(df, df_base)

    return df


# ============================================================
# RESUMO
# ============================================================

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
