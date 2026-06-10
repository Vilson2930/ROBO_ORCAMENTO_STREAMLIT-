# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — integração segura com Transaction Engine
#
# Correções principais:
# - NÃO transforma float 169.95 em 16995
# - NÃO confunde data 01/06 com parcela sem contexto
# - Usa campos novos do transaction_engine.py
# - Preserva fallback por texto bruto
# - Aplica trava de sanidade contra valores absurdos
# ============================================================

import re
import pandas as pd
import unicodedata


TOLERANCIA_VALOR = 0.15
MAX_TOTAL_PARCELAS = 60
MAX_VALOR_PARCELA = 50000.0
MAX_VALOR_TOTAL_COMPRA = 500000.0


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
    - Se já for número, retorna float direto.
    - Se vier como '169,95', converte para 169.95.
    - Se vier como '1.699,95', converte para 1699.95.
    - Evita transformar 169.95 em 16995.
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

PADRAO_NX_DE = re.compile(
    r"(?P<qtd>\d{1,2})\s*[Xx]\s*(?:DE|POR)?\s*R?\$?\s*(?P<valor>[\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
    re.IGNORECASE
)

PADRAO_PARC_EXPLICITA = re.compile(
    r"\b(?:PARC|PARC\.|PARCELA|PARCELADO|COMPRA PARCELADA)\.?\s*"
    r"(?P<atual>\d{1,2})\s*(?:/|DE)\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

PADRAO_PARC_BARRA = re.compile(
    r"\b(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

PADRAO_PARC_DE = re.compile(
    r"\b(?P<atual>\d{1,2})\s*DE\s*(?P<total>\d{1,2})\b",
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

PADRAO_DATA = re.compile(
    r"\b\d{2}/\d{2}(?:/\d{4})?\b",
    re.IGNORECASE
)


TERMOS_BLOQUEADOS = [
    "PAGAMENTO", "PIX", "BOLETO", "ESTORNO", "CREDITO", "CRÉDITO",
    "JUROS", "IOF", "ENCARGOS", "ROTATIVO", "TOTAL DA FATURA",
    "DESPESAS DA FATURA", "LIMITE", "VENCIMENTO", "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO", "PAGAMENTO TOTAL", "SALDO", "CET"
]


# ============================================================
# VALIDAÇÕES
# ============================================================

def contem_bloqueado(texto):
    texto = normalizar_texto(texto)
    return any(normalizar_texto(t) in texto for t in TERMOS_BLOQUEADOS)


def limpar_compra(texto):
    texto = normalizar_texto(texto)
    texto = PADRAO_NX_DE.sub(" ", texto)
    texto = PADRAO_PARC_EXPLICITA.sub(" ", texto)
    texto = PADRAO_NX.sub(" ", texto)
    texto = PADRAO_EM_NX.sub(" ", texto)
    texto = PADRAO_N_PARCELAS.sub(" ", texto)
    texto = PADRAO_VALOR.sub(" ", texto)
    texto = PADRAO_DATA.sub(" ", texto)
    texto = re.sub(r"[*]+", " ", texto)
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

    if contem_bloqueado(compra):
        return False

    if not re.search(r"[A-Z]", compra):
        return False

    return True


def numero_valido(valor):
    try:
        valor = float(valor)
        return valor > 0
    except Exception:
        return False


def parcela_valida(atual, total):
    try:
        atual = int(atual)
        total = int(total)
    except Exception:
        return False

    if total <= 0:
        return False

    if total > MAX_TOTAL_PARCELAS:
        return False

    if atual < 0:
        return False

    if atual > total:
        return False

    return True


def valores_sanos(valor_parcela, total_parcelas):
    try:
        valor_parcela = float(valor_parcela)
        total_parcelas = int(total_parcelas)
    except Exception:
        return False

    if valor_parcela <= 0:
        return False

    if valor_parcela > MAX_VALOR_PARCELA:
        return False

    if total_parcelas <= 0 or total_parcelas > MAX_TOTAL_PARCELAS:
        return False

    valor_total = valor_parcela * total_parcelas

    if valor_total > MAX_VALOR_TOTAL_COMPRA:
        return False

    return True


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

        if parcela_valida(atual, total):
            return atual, total, 0.0, "PARCELA_EXPLICITA"

    m = PADRAO_NX_DE.search(texto)
    if m:
        total = int(m.group("qtd"))
        valor_parcela = converter_valor(m.group("valor"))

        if parcela_valida(0, total) and valor_parcela > 0:
            return 0, total, valor_parcela, "NX_DE_VALOR"

    m = PADRAO_EM_NX.search(texto)
    if m:
        total = int(m.group("total"))

        if parcela_valida(0, total):
            return 0, total, 0.0, "EM_NX"

    m = PADRAO_NX.search(texto)
    if m:
        total = int(m.group("total"))

        if parcela_valida(0, total):
            return 0, total, 0.0, "NX"

    m = PADRAO_N_PARCELAS.search(texto)
    if m:
        total = int(m.group("total"))

        if parcela_valida(0, total):
            return 0, total, 0.0, "N_PARCELAS"

    # Formatos 01/06 e 01 DE 06 só são aceitos com contexto explícito.
    # Isso impede confundir datas com parcelas.
    tem_contexto = any(p in texto for p in [
        "PARC", "PARCELA", "PARCELADO", "COMPRA", "SEM JUROS",
        "PARCELAS", "PRESTACOES", "PRESTAÇÕES"
    ])

    if tem_contexto:
        m = PADRAO_PARC_BARRA.search(texto)
        if m:
            atual = int(m.group("atual"))
            total = int(m.group("total"))

            if parcela_valida(atual, total):
                return atual, total, 0.0, "BARRA_CONTEXTO"

        m = PADRAO_PARC_DE.search(texto)
        if m:
            atual = int(m.group("atual"))
            total = int(m.group("total"))

            if parcela_valida(atual, total):
                return atual, total, 0.0, "DE_CONTEXTO"

    return 0, 0, 0.0, ""


# ============================================================
# REGISTRO PADRÃO
# ============================================================

def criar_registro(
    arquivo,
    compra,
    categoria,
    ultima_parcela,
    total_parcelas,
    valor_parcela,
    descricao_detectada,
    tipo_detectado,
    confianca_extracao=0,
):
    if not compra_valida(compra):
        return None

    ultima_parcela = int(ultima_parcela or 0)
    total_parcelas = int(total_parcelas or 0)
    valor_parcela = float(valor_parcela or 0)

    if not parcela_valida(ultima_parcela, total_parcelas):
        return None

    if not valores_sanos(valor_parcela, total_parcelas):
        return None

    return {
        "arquivo_fatura": arquivo,
        "compra": limpar_compra(compra),
        "categoria": categoria or "Outros",
        "ultima_parcela": ultima_parcela,
        "total_parcelas": total_parcelas,
        "valor_parcela": valor_parcela,
        "descricao_detectada": str(descricao_detectada or ""),
        "tipo_detectado": str(tipo_detectado or ""),
        "valor_total_informado": round(total_parcelas * valor_parcela, 2),
        "confianca_extracao": int(confianca_extracao or 0),
    }


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
        categoria = linha.get("categoria", "Outros")
        arquivo = linha.get("arquivo_fatura", "")

        valor_lancamento = converter_valor(linha.get("valor", 0))
        valor_parcela_col = converter_valor(linha.get("valor_parcela", 0))

        parcelado = bool(linha.get("parcelado", False))

        parcela_atual = int(pd.to_numeric(linha.get("parcela_atual", 0), errors="coerce") or 0)
        total_parcelas = int(pd.to_numeric(linha.get("total_parcelas", 0), errors="coerce") or 0)

        tipo_parcela = str(linha.get("tipo_parcela", ""))
        confianca = int(pd.to_numeric(linha.get("confianca_extracao", 0), errors="coerce") or 0)

        # Caminho principal: campos estruturados do transaction_engine
        if parcelado and total_parcelas > 0:
            compra = limpar_compra(descricao)

            if not compra_valida(compra):
                compra = limpar_compra(descricao_original)

            if not compra_valida(compra):
                compra = limpar_compra(linha_original_pdf)

            if not compra_valida(compra):
                continue

            # Regra segura:
            # valor_parcela vem primeiro da coluna estruturada.
            # Se não existir, usa valor do lançamento.
            valor_parcela = valor_parcela_col if valor_parcela_col > 0 else valor_lancamento

            registro = criar_registro(
                arquivo=arquivo,
                compra=compra,
                categoria=categoria,
                ultima_parcela=parcela_atual,
                total_parcelas=total_parcelas,
                valor_parcela=valor_parcela,
                descricao_detectada=linha_original_pdf or descricao_original,
                tipo_detectado=f"TX_ENGINE_{tipo_parcela or 'PARCELADO'}",
                confianca_extracao=confianca,
            )

            if registro:
                registros.append(registro)

            continue

        # Caminho de compatibilidade: tenta extrair do texto
        texto_busca = " ".join([
            descricao,
            descricao_original,
            linha_original_pdf
        ])

        if contem_bloqueado(texto_busca):
            continue

        atual, total, valor_parcela_detectado, tipo = extrair_parcela_texto(texto_busca)

        if total <= 0:
            continue

        compra = limpar_compra(texto_busca)

        if not compra_valida(compra):
            continue

        valor_parcela = valor_parcela_detectado if valor_parcela_detectado > 0 else valor_lancamento

        registro = criar_registro(
            arquivo=arquivo,
            compra=compra,
            categoria=categoria,
            ultima_parcela=atual,
            total_parcelas=total,
            valor_parcela=valor_parcela,
            descricao_detectada=linha_original_pdf or descricao_original,
            tipo_detectado=f"DF_{tipo}",
            confianca_extracao=confianca,
        )

        if registro:
            registros.append(registro)

    return registros


# ============================================================
# EXTRAÇÃO A PARTIR DO TEXTO BRUTO DO PDF
# ============================================================

def extrair_parcelamentos_documento(texto, arquivo=""):
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    registros = []

    contexto = []
    ultimo_valor_total = None

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if linha_norm.startswith("--- PAGINA"):
            contexto = []
            ultimo_valor_total = None
            continue

        atual, total, valor_parcela_detectado, tipo = extrair_parcela_texto(linha_norm)

        if total > 0:
            valores = [converter_valor(v) for v in PADRAO_VALOR.findall(linha_norm)]
            valor_total = None

            if valores:
                candidatos_total = [
                    v for v in valores
                    if valor_parcela_detectado <= 0 or v > valor_parcela_detectado
                ]

                if candidatos_total:
                    valor_total = max(candidatos_total)

            if valor_parcela_detectado > 0:
                valor_parcela = valor_parcela_detectado

            elif ultimo_valor_total and total > 0:
                valor_parcela = round(ultimo_valor_total / total, 2)
                valor_total = ultimo_valor_total

            else:
                valor_parcela = 0.0

            compra_linha = limpar_compra(linha_norm)
            compra_contexto = limpar_compra(" ".join(contexto[-5:]))

            compra = compra_linha if compra_valida(compra_linha) else compra_contexto

            registro = criar_registro(
                arquivo=arquivo,
                compra=compra,
                categoria="Outros",
                ultima_parcela=atual,
                total_parcelas=total,
                valor_parcela=valor_parcela,
                descricao_detectada=linha,
                tipo_detectado=f"DOC_{tipo}",
                confianca_extracao=0,
            )

            if registro:
                registros.append(registro)

            contexto = []
            ultimo_valor_total = None
            continue

        valores_linha = PADRAO_VALOR.findall(linha_norm)

        if valores_linha:
            candidatos = [converter_valor(v) for v in valores_linha]
            ultimo_valor_total = max(candidatos)

            sem_valor = limpar_compra(PADRAO_VALOR.sub(" ", linha_norm))

            if compra_valida(sem_valor):
                contexto.append(sem_valor)
                contexto = contexto[-5:]

            continue

        if compra_valida(linha_norm):
            contexto.append(linha_norm)
            contexto = contexto[-5:]

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

    base["compra_norm"] = base["compra"].apply(normalizar_texto)
    base["valor_parcela"] = pd.to_numeric(base["valor_parcela"], errors="coerce").fillna(0)
    base["total_parcelas"] = pd.to_numeric(base["total_parcelas"], errors="coerce").fillna(0).astype(int)
    base["ultima_parcela"] = pd.to_numeric(base["ultima_parcela"], errors="coerce").fillna(0).astype(int)

    if "confianca_extracao" not in base.columns:
        base["confianca_extracao"] = 0

    base["confianca_extracao"] = pd.to_numeric(base["confianca_extracao"], errors="coerce").fillna(0).astype(int)

    base = base[base["valor_parcela"] > 0]
    base = base[base["valor_parcela"] <= MAX_VALOR_PARCELA]
    base = base[base["total_parcelas"] > 0]
    base = base[base["total_parcelas"] <= MAX_TOTAL_PARCELAS]
    base = base[base["ultima_parcela"] <= base["total_parcelas"]]
    base = base[base["compra_norm"].str.len() >= 3]
    base = base[(base["valor_parcela"] * base["total_parcelas"]) <= MAX_VALOR_TOTAL_COMPRA]

    if base.empty:
        return pd.DataFrame(columns=colunas)

    consolidados = []

    for (compra_norm, total_parcelas), grupo_compra in base.groupby(
        ["compra_norm", "total_parcelas"],
        dropna=False
    ):
        grupo_compra = grupo_compra.copy()
        grupo_compra = grupo_compra.sort_values("valor_parcela")

        grupos_valor = []

        for _, row in grupo_compra.iterrows():
            inserido = False

            for g in grupos_valor:
                referencia = float(g[0]["valor_parcela"])
                atual = float(row["valor_parcela"])

                if abs(atual - referencia) <= TOLERANCIA_VALOR:
                    g.append(row)
                    inserido = True
                    break

            if not inserido:
                grupos_valor.append([row])

        for g in grupos_valor:
            grupo = pd.DataFrame(g)

            maior_parcela = int(grupo["ultima_parcela"].max())
            total = int(grupo["total_parcelas"].max())
            valor_parcela = float(grupo["valor_parcela"].median())

            if not parcela_valida(maior_parcela, total):
                continue

            if not valores_sanos(valor_parcela, total):
                continue

            compra = grupo.iloc[0]["compra"]
            categoria = grupo.iloc[0].get("categoria", "Outros")
            arquivo = grupo.iloc[-1].get("arquivo_fatura", "")

            tipos = " | ".join(grupo["tipo_detectado"].astype(str).unique())
            descricoes = " | ".join(grupo["descricao_detectada"].astype(str).unique()[:10])
            confianca = int(grupo["confianca_extracao"].max())

            if maior_parcela == 0:
                parcelas_pagas = 0
                parcelas_abertas = total
            else:
                parcelas_pagas = maior_parcela
                parcelas_abertas = max(total - maior_parcela, 0)

            valor_restante = parcelas_abertas * valor_parcela
            valor_pago = parcelas_pagas * valor_parcela
            valor_total_compra = total * valor_parcela

            if valor_total_compra > MAX_VALOR_TOTAL_COMPRA:
                continue

            if parcelas_abertas == 0:
                status = "QUITADO"
                classificacao = "QUITADO"
            else:
                status = "ABERTO"

                if len(grupo) >= 2 or maior_parcela >= 2 or "NX_DE" in tipos or "TX_ENGINE" in tipos:
                    classificacao = "CONFIRMADO"
                else:
                    classificacao = "CONFIRMADO_INICIAL"

            consolidados.append({
                "arquivo_fatura": arquivo,
                "compra": compra,
                "categoria": categoria,
                "ultima_parcela": maior_parcela,
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
    base["_busca"] = base[coluna_desc].apply(normalizar_texto)

    for idx, row in df_parcelamentos.iterrows():
        compra = normalizar_texto(row.get("compra", ""))
        chave = compra[:10]

        if not chave:
            continue

        match = base[base["_busca"].str.contains(chave, regex=False, na=False)]

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

    # 1. Principal: campos estruturados vindos do transaction_engine.py
    registros.extend(extrair_parcelamentos_transacoes(df_base))

    # 2. Fallback: texto bruto dos PDFs
    if isinstance(documentos, list):
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
