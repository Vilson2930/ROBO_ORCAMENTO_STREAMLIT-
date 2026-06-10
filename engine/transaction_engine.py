# ============================================================
# TRANSACTION ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — fonte única para parcelamentos
#
# Correções estruturais:
# - remove o leitor antigo de parcelamento em bloco da execução
# - remove leitura sem data com valor da execução
# - mantém block_reader como única fonte de parcelamentos
# - mantém leitura linha a linha para compras normais
# - evita duplicidade e inflação de parcelas futuras
# - preserva colunas esperadas pelo restante do sistema
# ============================================================

import re
import pandas as pd
import unicodedata


# ============================================================
# IMPORTS OPCIONAIS
# ============================================================

try:
    from engine.block_reader import ler_blocos
except Exception:
    ler_blocos = None

try:
    from engine.confidence import calcular_confianca
except Exception:
    calcular_confianca = None

try:
    from engine.normalizer import (
        normalizar_texto as normalizar_texto_externo,
        limpar_descricao as limpar_descricao_externa,
        converter_valor as converter_valor_externo,
        normalizar_merchant as normalizar_merchant_externo,
    )
except Exception:
    normalizar_texto_externo = None
    limpar_descricao_externa = None
    converter_valor_externo = None
    normalizar_merchant_externo = None


# ============================================================
# CONFIG
# ============================================================

MESES = {
    "jan": "01", "janeiro": "01",
    "fev": "02", "fevereiro": "02",
    "mar": "03", "marco": "03", "março": "03",
    "abr": "04", "abril": "04",
    "mai": "05", "maio": "05",
    "jun": "06", "junho": "06",
    "jul": "07", "julho": "07",
    "ago": "08", "agosto": "08",
    "set": "09", "setembro": "09",
    "out": "10", "outubro": "10",
    "nov": "11", "novembro": "11",
    "dez": "12", "dezembro": "12",
}

BLACKLIST = [
    "DESPESAS DA FATURA", "DESPESAS DO MES", "DESPESAS DO MÊS",
    "PAGAMENTO TOTAL", "PAGAMENTO MINIMO", "PAGAMENTO MÍNIMO",
    "PAGAMENTO ON LINE", "PAGAMENTO ONLINE", "PAGAMENTO -", "PAGAMENTO +",
    "PAGAMENTO PIX", "PAGAMENTO BOLETO", "PAGAMENTO VIA",
    "DEBITO AUTOMATICO", "DÉBITO AUTOMÁTICO",
    "PRECISA DE UMA FORCA", "PRECISA DE UMA FORÇA",
    "ENCARGOS FINANCEIROS", "ENCARGOS", "ROTATIVO",
    "TOTAL DA FATURA", "VALOR TOTAL DA FATURA", "TOTAL A PAGAR",
    "LIMITE", "VENCIMENTO", "FECHAMENTO", "MELHOR DIA",
    "PAGINA", "PÁGINA", "RESUMO", "FATURA",
    "SALDO", "CREDITO", "CRÉDITO", "ESTORNO",
    "DATA | DESCRICAO | VALOR", "DATA | DESCRIÇÃO | VALOR",
    "DATA DESCRICAO VALOR", "DATA DESCRIÇÃO VALOR",
]


# ============================================================
# PADRÕES
# ============================================================

PADRAO_DATA_VALOR = re.compile(
    r"(?P<data>\d{2}/\d{2}(?:/\d{4})?)\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})$",
    re.IGNORECASE
)

PADRAO_EXTENSO_VALOR = re.compile(
    r"(?P<dia>\d{1,2})\s+DE\s+(?P<mes>[A-ZÇ]+)\.?\s+(?P<ano>\d{4})\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})$",
    re.IGNORECASE
)

PADRAO_VALOR = re.compile(
    r"R?\$?\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
    re.IGNORECASE
)

PADRAO_DATA_CURTA = re.compile(r"\b\d{2}/\d{2}(?:/\d{4})?\b")


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_texto(texto):
    if normalizar_texto_externo:
        try:
            return normalizar_texto_externo(texto)
        except Exception:
            pass

    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def limpar_descricao(descricao):
    if limpar_descricao_externa:
        try:
            return limpar_descricao_externa(descricao)
        except Exception:
            pass

    descricao = str(descricao or "")
    descricao = re.sub(r"R?\$?\s*[\d\.]+,\d{2}", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"R?\$?\s*\d+\.\d{2}", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"\b\d{2}/\d{2}(?:/\d{4})?\b", " ", descricao)
    descricao = re.sub(
        r"\b(?:PARC|PARC\.|PARCELA|PARCELADO|COMPRA\s+PARCELADA)\.?\s*\d{1,2}\s*(?:/|DE)\s*\d{1,2}\b",
        " ",
        descricao,
        flags=re.IGNORECASE
    )
    descricao = re.sub(r"\b\d{1,2}\s*X\b", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"\bEM\s*\d{1,2}\s*X\b", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"\b\d{1,2}\s*PARCELAS\b", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"COMPRA PARCELADA", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"PARCELADO SEM JUROS", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"PARCELADO", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"SEM JUROS", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"R\$", "", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"[*|]+", " ", descricao)
    descricao = re.sub(r"[-–—]+", " ", descricao)
    descricao = re.sub(r"\s+", " ", descricao)
    return descricao.strip(" -")


def converter_valor(valor):
    if converter_valor_externo:
        try:
            return converter_valor_externo(valor)
        except Exception:
            pass

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


def normalizar_merchant_local(texto):
    texto = limpar_descricao(texto)

    if normalizar_merchant_externo:
        try:
            return normalizar_merchant_externo(texto)
        except Exception:
            pass

    substituicoes = {
        "MERC PAGO": "MERCADO PAGO",
        "MERCPAGO": "MERCADO PAGO",
        "MERCADOPAGO": "MERCADO PAGO",
        "MP ": "MERCADO PAGO ",
        "MP*": "MERCADO PAGO ",
        "PAG SEGURO": "PAGSEGURO",
        "PAG*SEGURO": "PAGSEGURO",
        "GET NET": "GETNET",
        "SAFRA PAY": "SAFRAPAY",
        "BLU INSTITUICAO DE PAG": "BLU",
        "BLU INSTITUICAO": "BLU",
        "ADIQPAY": "ADIQ",
        "ADIQPLU": "ADIQ",
        "REDECARD": "REDE",
    }

    for antigo, novo in substituicoes.items():
        texto = texto.replace(antigo, novo)

    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def extrair_ano_arquivo(nome_arquivo):
    m = re.search(r"(20\d{2})", str(nome_arquivo))
    return m.group(1) if m else "2026"


# ============================================================
# VALIDAÇÕES
# ============================================================

def linha_bloqueada(linha):
    texto = normalizar_texto(linha)

    if not texto:
        return True

    for termo in BLACKLIST:
        if normalizar_texto(termo) in texto:
            return True

    if "PAGAMENTO" in texto:
        return True

    if "BOLETO" in texto or "PIX" in texto:
        return True

    if texto.endswith("+"):
        return True

    if " - +" in texto or "+ R$" in texto or " + " in texto:
        return True

    if len(texto) > 180:
        return True

    if texto.count("*") >= 8:
        return True

    return False


def descricao_valida(descricao):
    texto = normalizar_texto(descricao)

    if not texto:
        return False

    if linha_bloqueada(texto):
        return False

    if len(texto) < 3:
        return False

    if len(texto) > 120:
        return False

    if not re.search(r"[A-Z]", texto):
        return False

    # Rejeita descrição agregada de tabela.
    if " DATA " in f" {texto} " and " VALOR " in f" {texto} ":
        return False

    return True


def calcular_score_local(
    linha_original="",
    descricao="",
    valor=0,
    data=None,
    parcela_atual=None,
    parcela_total=None,
):
    if calcular_confianca:
        try:
            return calcular_confianca(
                linha_original=linha_original,
                descricao=descricao,
                valor=valor,
                data=data,
                parcela_atual=parcela_atual,
                parcela_total=parcela_total,
                merchant=descricao,
            )
        except Exception:
            pass

    score = 100
    motivos = []

    if not str(linha_original or "").strip():
        score -= 15
        motivos.append("SEM_LINHA_ORIGINAL")

    if not str(descricao or "").strip():
        score -= 20
        motivos.append("SEM_DESCRICAO")

    try:
        if float(valor) <= 0:
            score -= 30
            motivos.append("VALOR_INVALIDO")
    except Exception:
        score -= 30
        motivos.append("VALOR_INVALIDO")

    if data in [None, ""]:
        score -= 15
        motivos.append("SEM_DATA")

    if parcela_atual is not None and parcela_total is not None:
        try:
            if int(parcela_atual) > int(parcela_total):
                score -= 20
                motivos.append("PARCELA_MAIOR_QUE_TOTAL")
        except Exception:
            score -= 15
            motivos.append("ERRO_PARCELA")

    score = max(0, min(100, int(score)))

    if score >= 98:
        nivel = "EXCELENTE"
    elif score >= 90:
        nivel = "ALTA"
    elif score >= 75:
        nivel = "BOA"
    elif score >= 60:
        nivel = "MEDIA"
    else:
        nivel = "BAIXA"

    return {
        "confianca_extracao": score,
        "confidence_level": nivel,
        "confidence_version": "local",
        "motivos": motivos,
    }


# ============================================================
# MONTAGEM
# ============================================================

def montar_item(
    arquivo,
    data,
    descricao,
    valor,
    origem,
    linha_original,
    parcelado=False,
    parcela_atual=0,
    total_parcelas=0,
    parcelas_abertas=0,
    valor_parcela=0.0,
    tipo_parcela="",
):
    descricao_limpa = limpar_descricao(descricao)
    descricao_norm = normalizar_merchant_local(descricao_limpa)

    if not descricao_valida(descricao_norm):
        return None

    valor = converter_valor(valor)

    if valor <= 0:
        return None

    parcela_atual = int(parcela_atual or 0)
    total_parcelas = int(total_parcelas or 0)
    parcelas_abertas = int(parcelas_abertas or 0)
    valor_parcela = converter_valor(valor_parcela)

    if parcelado:
        if total_parcelas <= 0:
            return None

        if parcela_atual > total_parcelas:
            return None

        if valor_parcela <= 0:
            valor_parcela = valor

        if parcelas_abertas <= 0:
            parcelas_abertas = max(total_parcelas - parcela_atual, 0)

        # Travas de sanidade.
        if valor_parcela > 10000:
            return None

        if valor_parcela * max(total_parcelas, 1) > 500000:
            return None

    else:
        parcela_atual = 0
        total_parcelas = 0
        parcelas_abertas = 0
        valor_parcela = 0.0
        tipo_parcela = ""

    conf = calcular_score_local(
        linha_original=linha_original,
        descricao=descricao_norm,
        valor=valor,
        data=data,
        parcela_atual=parcela_atual if parcelado else None,
        parcela_total=total_parcelas if parcelado else None,
    )

    motivos = conf.get("motivos", [])

    if isinstance(motivos, list):
        motivos = "; ".join(motivos)

    return {
        "arquivo_fatura": arquivo,
        "data": data,
        "descricao_original": descricao_norm,
        "descricao_normalizada": descricao_norm,
        "valor": float(valor),
        "origem_extracao": origem,
        "parcelado": bool(parcelado),
        "parcela_atual": int(parcela_atual),
        "total_parcelas": int(total_parcelas),
        "parcelas_abertas": int(parcelas_abertas),
        "valor_parcela": float(valor_parcela),
        "tipo_parcela": tipo_parcela,
        "linha_original_pdf": str(linha_original or ""),
        "confianca_extracao": int(conf.get("confianca_extracao", conf.get("confidence_raw", 0)) or 0),
        "nivel_confianca": conf.get("confidence_level", conf.get("nivel_confianca", "")),
        "confidence_version": conf.get("confidence_version", ""),
        "confidence_motivos": motivos,
    }


# ============================================================
# EXTRAÇÃO LINHA A LINHA — COMPRAS NORMAIS
# ============================================================

def extrair_linha_numerica(linha, arquivo):
    m = PADRAO_DATA_VALOR.search(linha.strip())

    if not m:
        return None

    data = m.group("data")
    descricao_raw = m.group("descricao")
    valor = converter_valor(m.group("valor"))

    if len(data) == 5:
        data = f"{data}/{extrair_ano_arquivo(arquivo)}"

    return montar_item(
        arquivo=arquivo,
        data=data,
        descricao=descricao_raw,
        valor=valor,
        origem="data_valor",
        linha_original=linha,
        parcelado=False,
    )


def extrair_linha_extenso(linha, arquivo):
    linha_norm = normalizar_texto(linha)
    m = PADRAO_EXTENSO_VALOR.search(linha_norm)

    if not m:
        return None

    mes_nome = normalizar_texto(m.group("mes")).lower()
    mes = MESES.get(mes_nome)

    if not mes:
        return None

    dia = m.group("dia").zfill(2)
    ano = m.group("ano")
    descricao_raw = m.group("descricao")
    valor = converter_valor(m.group("valor"))

    return montar_item(
        arquivo=arquivo,
        data=f"{dia}/{mes}/{ano}",
        descricao=descricao_raw,
        valor=valor,
        origem="data_extenso",
        linha_original=linha,
        parcelado=False,
    )


# ============================================================
# EXTRAÇÃO DE PARCELAMENTOS — SOMENTE BLOCK_READER
# ============================================================

def extrair_blocos_inteligentes(texto, arquivo_origem=""):
    if ler_blocos is None:
        return []

    try:
        itens = ler_blocos(
            texto=texto,
            arquivo_origem=arquivo_origem,
            ano_padrao=extrair_ano_arquivo(arquivo_origem)
        )
    except Exception:
        return []

    resultados = []

    for item in itens:
        if not isinstance(item, dict):
            continue

        valor = converter_valor(item.get("valor", 0))
        descricao = item.get("descricao_original", "")
        data = item.get("data", f"01/01/{extrair_ano_arquivo(arquivo_origem)}")
        parcelado = bool(item.get("parcelado", False))
        pa = int(item.get("parcela_atual", 0) or 0)
        pt = int(item.get("total_parcelas", 0) or 0)
        vp = converter_valor(item.get("valor_parcela", 0))

        # block_reader só entra como parcelamento se realmente for parcelado.
        if not parcelado or pt <= 0:
            continue

        if valor <= 0 or not descricao_valida(descricao):
            continue

        novo = montar_item(
            arquivo=arquivo_origem,
            data=data,
            descricao=descricao,
            valor=valor,
            origem="block_reader",
            linha_original=item.get("linha_original_pdf", ""),
            parcelado=True,
            parcela_atual=pa,
            total_parcelas=pt,
            parcelas_abertas=max(pt - pa, 0),
            valor_parcela=vp if vp > 0 else valor,
            tipo_parcela=item.get("tipo_parcela", ""),
        )

        if novo is not None:
            resultados.append(novo)

    return resultados


# ============================================================
# ORQUESTRAÇÃO
# ============================================================

def extrair_transacoes_texto(texto, arquivo_origem=""):
    transacoes = []

    # 1. Fonte única de parcelamentos
    transacoes.extend(
        extrair_blocos_inteligentes(
            texto=texto,
            arquivo_origem=arquivo_origem
        )
    )

    # 2. Compras normais linha a linha
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]

    for linha in linhas:
        if linha_bloqueada(linha):
            continue

        item = extrair_linha_numerica(linha, arquivo_origem)

        if item is None:
            item = extrair_linha_extenso(linha, arquivo_origem)

        if item is not None:
            transacoes.append(item)

    return transacoes


def processar_transacoes(documentos):
    todas = []

    for doc in documentos:
        arquivo = doc.get("arquivo", "")
        texto = doc.get("texto", "")

        todas.extend(
            extrair_transacoes_texto(
                texto=texto,
                arquivo_origem=arquivo
            )
        )

    colunas = [
        "arquivo_fatura",
        "data",
        "descricao_original",
        "descricao_normalizada",
        "valor",
        "origem_extracao",
        "parcelado",
        "parcela_atual",
        "total_parcelas",
        "parcelas_abertas",
        "valor_parcela",
        "tipo_parcela",
        "linha_original_pdf",
        "confianca_extracao",
        "nivel_confianca",
        "confidence_version",
        "confidence_motivos",
    ]

    df = pd.DataFrame(todas, columns=colunas)

    if df.empty:
        return df

    df["data"] = pd.to_datetime(
        df["data"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    df = df.dropna(subset=["data"])

    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["valor"])
    df = df[df["valor"] > 0]

    df["descricao_original"] = df["descricao_original"].apply(limpar_descricao)
    df["descricao_normalizada"] = df["descricao_original"].apply(normalizar_merchant_local)

    df = df[df["descricao_original"].apply(descricao_valida)]

    df["parcelado"] = df["parcelado"].fillna(False).astype(bool)
    df["parcela_atual"] = pd.to_numeric(df["parcela_atual"], errors="coerce").fillna(0).astype(int)
    df["total_parcelas"] = pd.to_numeric(df["total_parcelas"], errors="coerce").fillna(0).astype(int)
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce").fillna(0).astype(int)
    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0)
    df["confianca_extracao"] = pd.to_numeric(df["confianca_extracao"], errors="coerce").fillna(0).astype(int)

    # Travas finais.
    df = df[~((df["parcelado"] == True) & (df["total_parcelas"] <= 0))]
    df = df[df["parcela_atual"] <= df["total_parcelas"].where(df["parcelado"], 0)]
    df = df[~((df["parcelado"] == True) & (df["valor_parcela"] <= 0))]
    df = df[~((df["parcelado"] == True) & (df["valor_parcela"] > 10000))]

    # Deduplicação profissional:
    # para compras normais, ignora campos de parcelamento;
    # para parceladas, usa estrutura de parcela.
    df_normais = df[df["parcelado"] == False].copy()
    df_parceladas = df[df["parcelado"] == True].copy()

    if not df_normais.empty:
        df_normais = df_normais.drop_duplicates(
            subset=[
                "arquivo_fatura",
                "data",
                "descricao_original",
                "valor",
            ]
        )

    if not df_parceladas.empty:
        df_parceladas = df_parceladas.drop_duplicates(
            subset=[
                "arquivo_fatura",
                "data",
                "descricao_original",
                "parcela_atual",
                "total_parcelas",
                "valor_parcela",
            ]
        )

    df = pd.concat([df_normais, df_parceladas], ignore_index=True)

    if df.empty:
        return df

    df = df.sort_values(["data", "descricao_original"]).reset_index(drop=True)

    return df


def resumo_transacoes(df_transacoes):
    if df_transacoes is None or df_transacoes.empty:
        return {
            "quantidade": 0,
            "valor_total": 0.0
        }

    return {
        "quantidade": int(len(df_transacoes)),
        "valor_total": float(df_transacoes["valor"].sum())
    }
