# ============================================================
# block_reader.py
# ORÇAMENTO INTELIGENTE
# Leitor inteligente de blocos de faturas brasileiras
# Versão corrigida — anti-agregação de tabela
# ============================================================

import re

from engine.normalizer import (
    normalizar_texto,
    limpar_descricao,
    converter_valor,
    descricao_valida,
)

from engine.confidence import calcular_confianca


PADRAO_VALOR = re.compile(
    r"R?\$?\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
    re.IGNORECASE
)

PADRAO_DATA = re.compile(
    r"\b(?P<data>\d{2}/\d{2}(?:/\d{4})?)\b",
    re.IGNORECASE
)

PADRAO_PARCELA_EXPLICITA = re.compile(
    r"""
    \b(?:PARCELA|PARC\.?|PARCELADO|COMPRA\s+PARCELADA)\s*
    (?P<atual>\d{1,2})
    \s*(?:/|DE)\s*
    (?P<total>\d{1,2})\b
    """,
    re.IGNORECASE | re.VERBOSE
)

PADRAO_PARCELA_BARRA = re.compile(
    r"\b(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

PADRAO_NX_DE = re.compile(
    r"""
    (?P<total>\d{1,2})
    \s*X\s*
    (?:DE|POR)?
    \s*
    R?\$?
    \s*
    (?P<valor>[\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})
    """,
    re.IGNORECASE | re.VERBOSE
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


TERMOS_CABECALHO = [
    "DATA DESCRICAO VALOR",
    "DATA DESCRIÇÃO VALOR",
    "DATA | DESCRICAO | VALOR",
    "DATA | DESCRIÇÃO | VALOR",
    "DESCRICAO VALOR",
    "DESCRIÇÃO VALOR",
]

TERMOS_BLOQUEADOS = [
    "PAGAMENTO",
    "PIX",
    "BOLETO",
    "ESTORNO",
    "CREDITO",
    "CRÉDITO",
    "TOTAL DA FATURA",
    "PAGAMENTO TOTAL",
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "LIMITE",
    "VENCIMENTO",
    "ENCARGOS",
    "JUROS",
    "IOF",
    "ROTATIVO",
]


def _linha_bloqueada(linha):
    texto = normalizar_texto(linha)

    if not texto:
        return True

    for termo in TERMOS_CABECALHO:
        if normalizar_texto(termo) in texto:
            return True

    for termo in TERMOS_BLOQUEADOS:
        if normalizar_texto(termo) in texto:
            return True

    if len(texto) > 180:
        return True

    return False


def _tem_contexto_parcela(texto):
    texto = normalizar_texto(texto)

    termos = [
        "PARC",
        "PARCELA",
        "PARCELADO",
        "COMPRA PARCELADA",
        "SEM JUROS",
        "PARCELAS",
        "PRESTACOES",
        "PRESTAÇÕES",
        " EM ",
    ]

    return any(t in texto for t in termos)


def _extrair_valor(linha):
    m = PADRAO_VALOR.search(str(linha or ""))

    if not m:
        return None

    valor = converter_valor(m.group(1))

    if valor <= 0:
        return None

    return valor


def _extrair_data(linha, ano_padrao="2026"):
    m = PADRAO_DATA.search(str(linha or ""))

    if not m:
        return None

    data = m.group("data")

    if len(data) == 5:
        data = f"{data}/{ano_padrao}"

    return data


def _extrair_parcela(linha):
    texto = normalizar_texto(linha)

    m = PADRAO_PARCELA_EXPLICITA.search(texto)

    if m:
        atual = int(m.group("atual"))
        total = int(m.group("total"))

        if 1 <= atual <= total <= 60:
            return atual, total, None, "PARCELA_EXPLICITA"

    m = PADRAO_NX_DE.search(texto)

    if m:
        total = int(m.group("total"))
        valor = converter_valor(m.group("valor"))

        if 1 <= total <= 60 and valor > 0:
            return 0, total, valor, "NX_DE_VALOR"

    m = PADRAO_EM_NX.search(texto)

    if m:
        total = int(m.group("total"))

        if 1 <= total <= 60:
            return 0, total, None, "EM_NX"

    m = PADRAO_NX.search(texto)

    if m:
        total = int(m.group("total"))

        if 1 <= total <= 60:
            return 0, total, None, "NX"

    m = PADRAO_N_PARCELAS.search(texto)

    if m:
        total = int(m.group("total"))

        if 1 <= total <= 60:
            return 0, total, None, "N_PARCELAS"

    # Formato 01/06 só é parcela se houver contexto explícito.
    # Sem contexto, é tratado como data.
    if _tem_contexto_parcela(texto):
        m = PADRAO_PARCELA_BARRA.search(texto)

        if m:
            atual = int(m.group("atual"))
            total = int(m.group("total"))

            if 1 <= atual <= total <= 60:
                return atual, total, None, "BARRA_CONTEXTO"

    return None, None, None, None


def _finalizar_bloco(bloco, arquivo_origem="", ano_padrao="2026"):
    if not bloco:
        return None

    bloco = [l for l in bloco if not _linha_bloqueada(l)]

    if not bloco:
        return None

    linha_original = " | ".join(bloco)
    texto_bloco = normalizar_texto(linha_original)

    # Trava anti-agregação:
    # Se o bloco tem várias datas e vários valores, provavelmente juntou várias compras.
    valores_encontrados = PADRAO_VALOR.findall(texto_bloco)
    datas_encontradas = PADRAO_DATA.findall(texto_bloco)

    if len(valores_encontrados) >= 2 and len(datas_encontradas) >= 2:
        return None

    valor = None
    data = None
    parcela_atual = None
    parcela_total = None
    valor_parcela = 0.0
    tipo_parcela = ""

    for linha in bloco:
        valor_linha = _extrair_valor(linha)

        if valor is None and valor_linha is not None:
            valor = valor_linha

        if data is None:
            data = _extrair_data(linha, ano_padrao=ano_padrao)

        pa, pt, vp, tipo = _extrair_parcela(linha)

        if pt is not None:
            parcela_atual = pa
            parcela_total = pt
            tipo_parcela = tipo or ""

            if vp is not None and vp > 0:
                valor_parcela = vp

    descricao = limpar_descricao(texto_bloco)

    if not descricao_valida(descricao):
        return None

    if valor is None and valor_parcela > 0:
        valor = valor_parcela

    if valor is None or valor <= 0:
        return None

    parcelado = parcela_total is not None

    if parcelado and valor_parcela <= 0:
        valor_parcela = valor

    # Travas de segurança.
    if valor > 100000:
        return None

    if valor_parcela and valor_parcela > 10000:
        return None

    confianca = calcular_confianca(
        linha_original=linha_original,
        descricao=descricao,
        valor=valor,
        data=data,
        parcela_atual=parcela_atual,
        parcela_total=parcela_total,
        merchant=descricao,
    )

    return {
        "arquivo_fatura": arquivo_origem,
        "data": data or f"01/01/{ano_padrao}",
        "descricao_original": descricao,
        "valor": float(valor),
        "origem_extracao": "block_reader",
        "parcelado": bool(parcelado),
        "parcela_atual": int(parcela_atual or 0),
        "total_parcelas": int(parcela_total or 0),
        "parcelas_abertas": max(
            int((parcela_total or 0) - (parcela_atual or 0)),
            0
        ) if parcelado else 0,
        "valor_parcela": float(valor_parcela or 0.0),
        "linha_original_pdf": linha_original,
        "tipo_parcela": tipo_parcela,
        "confianca_extracao": confianca.get("confianca_extracao", 0),
        "nivel_confianca": confianca.get("confidence_level", ""),
        "confidence_version": confianca.get("confidence_version", ""),
        "confidence_motivos": "; ".join(confianca.get("motivos", [])),
    }


def ler_blocos(texto, arquivo_origem="", ano_padrao="2026"):
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]

    resultados = []
    contexto = []

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if linha_norm.startswith("--- PAGINA"):
            contexto = []
            continue

        if _linha_bloqueada(linha_norm):
            contexto = []
            continue

        tem_valor = PADRAO_VALOR.search(linha_norm) is not None
        pa, pt, vp, tipo = _extrair_parcela(linha_norm)
        tem_parcela = pt is not None

        # Linha completa com valor.
        # Não acumula 6 linhas. Isso era o bug que juntava compras diferentes.
        if tem_valor:
            item = _finalizar_bloco(
                [linha],
                arquivo_origem=arquivo_origem,
                ano_padrao=ano_padrao
            )

            if item:
                resultados.append(item)

            contexto = []
            continue

        # Linha sem valor: guarda apenas contexto curto.
        contexto.append(linha)
        contexto = contexto[-2:]

        # Linha com parcela explícita sem valor: usa contexto curto.
        if tem_parcela and contexto:
            item = _finalizar_bloco(
                contexto,
                arquivo_origem=arquivo_origem,
                ano_padrao=ano_padrao
            )

            if item:
                resultados.append(item)

            contexto = []

    return resultados
