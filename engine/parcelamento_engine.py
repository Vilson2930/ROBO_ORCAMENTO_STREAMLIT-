# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — saneador/consolidador
#
# Objetivo:
# - corrigir valores vindos errados do transaction_engine
# - eliminar DOC_* administrativo e duplicado
# - manter TX_ENGINE como fonte principal
# - consolidar a mesma compra em uma única linha
# - calcular saldo futuro com matemática limpa
# ============================================================

import re
import pandas as pd
import unicodedata


# ============================================================
# CONFIGURAÇÕES
# ============================================================

TOLERANCIA_VALOR = 0.20
MAX_TOTAL_PARCELAS = 60
MAX_VALOR_PARCELA = 20000.0


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
    Conversor seguro.
    Não transforma 169.95 em 16995.
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

PADRAO_PARCELA = re.compile(
    r"\b(?:PARC|PARC\.|PARCELA|PARCELADO|COMPRA PARCELADA)\.?\s*"
    r"(?P<atual>\d{1,2})\s*(?:/|DE)\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

PADRAO_NX_DE = re.compile(
    r"\b(?P<qtd>\d{1,2})\s*X\s*(?:DE|POR)?\s*R?\$?\s*(?P<valor>[\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
    re.IGNORECASE
)

PADRAO_DATA_NUMERICA = re.compile(r"\b\d{2}/\d{2}(?:/\d{4})?\b")

PADRAO_DATA_EXTENSO = re.compile(
    r"\b\d{1,2}\s+DE\s+[A-Z]{3,9}\.?\s+\d{4}\b",
    re.IGNORECASE
)


TERMOS_BLOQUEADOS = [
    "PAGAMENTO", "PIX", "BOLETO", "ESTORNO", "CREDITO", "CRÉDITO",
    "JUROS", "IOF", "ENCARGOS", "ROTATIVO", "TOTAL DA FATURA",
    "DESPESAS DA FATURA", "LIMITE", "VENCIMENTO", "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO", "PAGAMENTO TOTAL", "SALDO", "CET",
    "CANCELANDO O AGENDAMENTO", "PARCELAMENTO É REALIZADO AUTOMATICAMENTE",
    "PARCELAMENTO E REALIZADO AUTOMATICAMENTE", "JUROS REMUNERATORIOS",
    "JUROS REMUNERATÓRIOS", "EM ATE 15 PARCELAS", "EM ATÉ 15 PARCELAS",
    "DEBITO AUTOMATICO", "DÉBITO AUTOMÁTICO"
]


# ============================================================
# UTILITÁRIOS
# ============================================================

def contem_bloqueado(texto):
    texto = normalizar_texto(texto)
    return any(normalizar_texto(t) in texto for t in TERMOS_BLOQUEADOS)


def limpar_compra(texto):
    texto = normalizar_texto(texto)

    texto = PADRAO_DATA_EXTENSO.sub(" ", texto)
    texto = PADRAO_DATA_NUMERICA.sub(" ", texto)
    texto = PADRAO_PARCELA.sub(" ", texto)
    texto = PADRAO_NX_DE.sub(" ", texto)
    texto = PADRAO_VALOR.sub(" ", texto)

    texto = re.sub(r"\b\d{1,2}\s*X\b", " ", texto)
    texto = re.sub(r"\bEM\s*\d{1,2}\s*X\b", " ", texto)
    texto = re.sub(r"\b\d{1,2}\s*(?:PARCELAS|PRESTACOES|PRESTAÇÕES)\b", " ", texto)
    texto = re.sub(r"COMPRA PARCELADA", " ", texto)
    texto = re.sub(r"PARCELADO SEM JUROS", " ", texto)
    texto = re.sub(r"PARCELADO", " ", texto)
    texto = re.sub(r"SEM JUROS", " ", texto)
    texto = re.sub(r"[*|]+", " ", texto)
    texto = re.sub(r"[-–—]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip(" -")


def compra_valida(compra):
    compra = normalizar_texto(compra)

    if not compra:
        return False

    if len(compra) < 3:
        return False

    if len(compra) > 90:
        return False

    if contem_bloqueado(compra):
        return False

    if not re.search(r"[A-Z]", compra):
        return False

    return True


def chave_compra(compra):
    """
    Chave estável para consolidar:
    '25 DE MAI. 2026 HEVILLYN FARMACEUTICA'
    e 'HEVILLYN FARMACEUTICA' viram a mesma base.
    """
    c = limpar_compra(compra)
    c = normalizar_texto(c)
    c = re.sub(r"[^A-Z0-9 ]", " ", c)
    c = re.sub(r"\s+", " ", c).strip()

    substituicoes = {
        "MERC PAGO": "MERCADO PAGO",
        "MERCPAGO": "MERCADO PAGO",
        "MERCADOPAGO": "MERCADO PAGO",
        "MP ": "MERCADO PAGO ",
        "ADIQPLU": "ADIQ",
        "ADIQPAY": "ADIQ",
        "BLU INSTITUICAO DE PAG": "BLU",
        "BLU INSTITUICAO": "BLU",
    }

    for antigo, novo in substituicoes.items():
        c = c.replace(antigo, novo)

    c = re.sub(r"\s+", " ", c).strip()
    return c


def encontrar_coluna_descricao(df):
    for col in [
        "descricao_normalizada", "descricao_original", "merchant",
        "descricao", "estabelecimento", "compra", "texto", "lancamento",
    ]:
        if col in df.columns:
            return col

    for col in df.columns:
        if df[col].dtype == "object":
            return col

    return None


def extrair_valor_da_evidencia(texto):
    """
    Fonte mais confiável para corrigir:
    'R$ 122,55' -> 122.55
    'R$ 291,70' -> 291.70
    """
    valores = [converter_valor(v) for v in PADRAO_VALOR.findall(str(texto or ""))]
    valores = [v for v in valores if v > 0]

    if not valores:
        return 0.0

    # Em linhas de compra parcelada normalmente há um único valor monetário.
    return valores[-1]


def corrigir_valor_por_evidencia(valor_atual, evidencia):
    valor_evidencia = extrair_valor_da_evidencia(evidencia)

    if valor_evidencia > 0:
        return valor_evidencia

    valor_atual = converter_valor(valor_atual)

    # Correção defensiva para inteiros inflados quando não houver evidência textual.
    # 12255 -> 122.55, 2917 -> 291.70, 699 -> 69.90
    if valor_atual >= 1000 and abs(valor_atual - int(valor_atual)) < 0.0001:
        return round(valor_atual / 100, 2)

    if valor_atual >= 100 and abs(valor_atual - int(valor_atual)) < 0.0001:
        return round(valor_atual / 10, 2)

    return valor_atual


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

        if contem_bloqueado(evidencia):
            continue

        parcelado = bool(linha.get("parcelado", False))
        total_parcelas = int(pd.to_numeric(linha.get("total_parcelas", 0), errors="coerce") or 0)

        if not parcelado or total_parcelas <= 0:
            continue

        parcela_atual = int(pd.to_numeric(linha.get("parcela_atual", 0), errors="coerce") or 0)

        if parcela_atual < 0 or parcela_atual > total_parcelas or total_parcelas > MAX_TOTAL_PARCELAS:
            continue

        valor_parcela_raw = linha.get("valor_parcela", 0)
        valor_lancamento = linha.get("valor", 0)

        valor_parcela = corrigir_valor_por_evidencia(valor_parcela_raw, evidencia)

        if valor_parcela <= 0:
            valor_parcela = corrigir_valor_por_evidencia(valor_lancamento, evidencia)

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
            "arquivo_fatura": linha.get("arquivo_fatura", ""),
            "compra": compra,
            "compra_key": chave_compra(compra),
            "categoria": linha.get("categoria", "Outros"),
            "ultima_parcela": parcela_atual,
            "total_parcelas": total_parcelas,
            "valor_parcela": float(valor_parcela),
            "descricao_detectada": evidencia,
            "tipo_detectado": f"TX_ENGINE_{linha.get('tipo_parcela', 'PARCELADO')}",
            "confianca_extracao": int(pd.to_numeric(linha.get("confianca_extracao", 0), errors="coerce") or 0),
            "prioridade_origem": 2,
        })

    return registros


# ============================================================
# FALLBACK DOCUMENTAL
# ============================================================

def extrair_parcelamentos_documento(texto, arquivo=""):
    """
    Fallback propositalmente conservador.

    Só aceita linha com:
    - parcela explícita na MESMA linha
    - valor monetário na MESMA linha
    - sem texto administrativo

    Não aceita '15 parcelas' de contrato/aviso do banco.
    """
    registros = []

    for linha in [l.strip() for l in str(texto or "").splitlines() if l.strip()]:
        linha_norm = normalizar_texto(linha)

        if contem_bloqueado(linha_norm):
            continue

        m = PADRAO_PARCELA.search(linha_norm)
        if not m:
            continue

        atual = int(m.group("atual"))
        total = int(m.group("total"))

        if not (1 <= atual <= total <= MAX_TOTAL_PARCELAS):
            continue

        valor = extrair_valor_da_evidencia(linha_norm)

        if valor <= 0 or valor > MAX_VALOR_PARCELA:
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
            "valor_parcela": float(valor),
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

    base["compra_key"] = base.get("compra_key", base["compra"].apply(chave_compra))
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
    base = base[base["compra_key"].str.len() >= 3]

    if base.empty:
        return pd.DataFrame(columns=colunas)

    consolidados = []

    # Consolida por compra_key + total_parcelas.
    # Dentro do grupo, TX vence DOC.
    for (compra_key, total), grupo in base.groupby(["compra_key", "total_parcelas"], dropna=False):
        grupo = grupo.copy()

        # Remove duplicatas exatas de parcela.
        grupo = grupo.sort_values(
            ["prioridade_origem", "confianca_extracao"],
            ascending=[False, False]
        )

        grupo = grupo.drop_duplicates(
            subset=["compra_key", "total_parcelas", "ultima_parcela", "valor_parcela"],
            keep="first"
        )

        # Se existe TX_ENGINE no grupo, descarta DOC duplicado da mesma compra.
        if grupo["tipo_detectado"].astype(str).str.contains("TX_ENGINE", na=False).any():
            grupo = grupo[grupo["tipo_detectado"].astype(str).str.contains("TX_ENGINE", na=False)].copy()

        # Agrupa valores próximos.
        valores = grupo["valor_parcela"].tolist()
        valor_parcela = float(pd.Series(valores).median())

        # Se houver valores muito divergentes dentro da mesma compra, fica com o valor do maior score.
        if len(valores) > 1:
            max_v = max(valores)
            min_v = min(valores)
            if max_v - min_v > TOLERANCIA_VALOR:
                melhor = grupo.sort_values(
                    ["prioridade_origem", "confianca_extracao"],
                    ascending=[False, False]
                ).iloc[0]
                valor_parcela = float(melhor["valor_parcela"])

        maior_parcela = int(grupo["ultima_parcela"].max())
        total_parcelas = int(total)

        parcelas_pagas = maior_parcela
        parcelas_abertas = max(total_parcelas - maior_parcela, 0)

        valor_pago = parcelas_pagas * valor_parcela
        valor_restante = parcelas_abertas * valor_parcela
        valor_total_compra = total_parcelas * valor_parcela

        status = "QUITADO" if parcelas_abertas == 0 else "ABERTO"

        tipos = " | ".join(grupo["tipo_detectado"].astype(str).unique())
        descricoes = " | ".join(grupo["descricao_detectada"].astype(str).unique()[:8])
        confianca = int(grupo["confianca_extracao"].max())

        melhor_linha = grupo.sort_values(
            ["prioridade_origem", "confianca_extracao"],
            ascending=[False, False]
        ).iloc[0]

        if status == "QUITADO":
            classificacao = "QUITADO"
        elif "TX_ENGINE" in tipos or len(grupo) >= 2:
            classificacao = "CONFIRMADO"
        else:
            classificacao = "CONFIRMADO_INICIAL"

        consolidados.append({
            "arquivo_fatura": melhor_linha.get("arquivo_fatura", ""),
            "compra": melhor_linha.get("compra", compra_key),
            "categoria": melhor_linha.get("categoria", "Outros"),
            "ultima_parcela": maior_parcela,
            "total_parcelas": total_parcelas,
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
    base["_busca"] = base[coluna_desc].apply(chave_compra)

    for idx, row in df_parcelamentos.iterrows():
        chave = chave_compra(row.get("compra", ""))

        if not chave:
            continue

        match = base[base["_busca"].str.contains(chave[:12], regex=False, na=False)]

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

    # Fonte principal: transações estruturadas.
    registros.extend(extrair_parcelamentos_transacoes(df_base))

    # Fallback conservador, usado apenas quando não houver df_base com parcelamentos.
    tem_tx = len(registros) > 0

    if not tem_tx and isinstance(documentos, list):
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
