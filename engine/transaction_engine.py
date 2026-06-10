# ============================================================
# TRANSACTION ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — leitura por seção
#
# Corrige:
# - compras à vista da Caixa/Nubank/Inter
# - compras parceladas
# - valores com D/C no final: 37,89D / 1.561,74D
# - não depende apenas de regex solto
# ============================================================

import re
import pandas as pd
import unicodedata


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
    "ENCARGOS FINANCEIROS", "ENCARGOS", "ROTATIVO",
    "TOTAL DA FATURA", "VALOR TOTAL DA FATURA", "TOTAL A PAGAR",
    "LIMITE", "VENCIMENTO", "FECHAMENTO", "MELHOR DIA",
    "PAGINA", "PÁGINA", "RESUMO", "FATURA",
    "SALDO", "CREDITO", "CRÉDITO", "ESTORNO",
    "OBRIGADO PELO PAGAMENTO",
    "TOTAL DA FATURA ANTERIOR",
    "AJUSTE CRED",
    "AJUSTE CREDITO",
    "AJUSTE CRÉDITO",
    "IOF", "CET", "JUROS", "MULTA", "MORA",
    "OPÇÕES PARA PAGAMENTO", "OPCOES PARA PAGAMENTO",
    "PARCELAMENTO DE FATURA",
    "TOTAL COMPRAS", "TOTAL FINAL", "LEGENDA",
    "INFORMAÇÕES COMPLEMENTARES", "INFORMACOES COMPLEMENTARES",
    "PROGRAMA DE PONTOS", "GUIA DE CONSUMO",
]

CABECALHOS = [
    "DATA DESCRICAO CIDADE PAIS VALOR",
    "DATA DESCRIÇÃO CIDADE/PAÍS VALOR",
    "DATA DESCRIÇÃO CIDADE PAÍS VALOR",
    "DATA DESCRICAO VALOR",
    "DATA DESCRIÇÃO VALOR",
    "VALOR U$$",
    "CRÉDITO/DÉBITO",
    "CREDITO/DEBITO",
]

PADRAO_DATA_VALOR = re.compile(
    r"(?P<data>\d{2}/\d{2}(?:/\d{4})?)\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<valor>R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|R?\$?\s*\d+,\d{2})\s*(?P<dc>[DC])?$",
    re.IGNORECASE,
)

PADRAO_EXTENSO_VALOR = re.compile(
    r"(?P<dia>\d{1,2})\s+DE\s+(?P<mes>[A-ZÇ]+)\.?\s+(?P<ano>\d{4})\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<valor>R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}|R?\$?\s*\d+,\d{2})\s*(?P<dc>[DC])?$",
    re.IGNORECASE,
)

PADRAO_PARCELA_DE = re.compile(
    r"\b(?P<atual>\d{1,2})\s*DE\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)

PADRAO_PARCELA_BARRA = re.compile(
    r"\b(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)

PADRAO_NX = re.compile(
    r"\b(?P<total>\d{1,2})\s*X\b",
    re.IGNORECASE,
)

PADRAO_VALOR = re.compile(
    r"R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\s*[DC]?",
    re.IGNORECASE,
)


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
    texto = texto.replace("R$", "").replace(" ", "")
    texto = re.sub(r"[DCdc]$", "", texto)

    try:
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
            return float(texto)
        return float(texto)
    except Exception:
        return 0.0


def extrair_ano_arquivo(nome_arquivo):
    m = re.search(r"(20\d{2})", str(nome_arquivo))
    return m.group(1) if m else "2026"


def limpar_descricao(descricao):
    descricao = str(descricao or "")
    descricao = PADRAO_VALOR.sub(" ", descricao)
    descricao = re.sub(r"\b\d{2}/\d{2}(?:/\d{4})?\b", " ", descricao)
    descricao = re.sub(r"\b\d{1,2}\s*DE\s*\d{1,2}\b", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"\b\d{1,2}\s*/\s*\d{1,2}\b", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"\b\d{1,2}\s*X\b", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"R\$", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"[*|]+", " ", descricao)
    descricao = re.sub(r"[-–—]+", " ", descricao)
    descricao = re.sub(r"\s+", " ", descricao)
    return descricao.strip(" -")


def linha_cabecalho(linha):
    texto = normalizar_texto(linha)
    return any(normalizar_texto(cab) in texto for cab in CABECALHOS)


def linha_bloqueada(linha):
    texto = normalizar_texto(linha)

    if not texto:
        return True

    if linha_cabecalho(texto):
        return True

    for termo in BLACKLIST:
        if normalizar_texto(termo) in texto:
            return True

    if texto.endswith("C") and PADRAO_VALOR.search(texto):
        return True

    if "PAGAMENTO" in texto:
        return True

    if "BOLETO" in texto or "PIX" in texto:
        return True

    if len(texto) > 180:
        return True

    if texto.count("/") > 6:
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

    return True


def detectar_secao(linha, estado_atual=None):
    texto = normalizar_texto(linha)

    if "COMPRAS PARCELADAS" in texto or "DESPESAS A VENCER" in texto:
        return "PARCELADAS"

    if "COMPRAS (" in texto or texto == "COMPRAS":
        return "AVISTA"

    if texto == "ANUIDADE" or texto.startswith("ANUIDADE "):
        return "ANUIDADE"

    if (
        "TOTAL COMPRAS PARCELADAS" in texto
        or "TOTAL COMPRAS" in texto
        or "TOTAL FINAL" in texto
        or "VALOR TOTAL DESTA FATURA" in texto
        or "LEGENDA" in texto
        or "DEMONSTRATIVO" in texto
        or "ENCARGOS" in texto
    ):
        return None

    return estado_atual


def extrair_parcela(descricao):
    texto = normalizar_texto(descricao)

    m = PADRAO_PARCELA_DE.search(texto)

    if m:
        atual = int(m.group("atual"))
        total = int(m.group("total"))

        if 1 <= atual <= total <= 60:
            return atual, total, "DE"

    m = PADRAO_PARCELA_BARRA.search(texto)

    if m:
        atual = int(m.group("atual"))
        total = int(m.group("total"))

        if 1 <= atual <= total <= 60:
            return atual, total, "BARRA"

    m = PADRAO_NX.search(texto)

    if m:
        total = int(m.group("total"))

        if 1 <= total <= 60:
            return 0, total, "NX"

    return 0, 0, ""


def montar_item(
    arquivo,
    data,
    descricao,
    valor,
    origem,
    parcelado=False,
    parcela_atual=0,
    total_parcelas=0,
    tipo_parcela="",
    linha_original_pdf="",
):
    descricao_limpa = limpar_descricao(descricao)

    if not descricao_valida(descricao_limpa):
        return None

    valor = converter_valor(valor)

    if valor <= 0:
        return None

    if len(data) == 5:
        data = f"{data}/{extrair_ano_arquivo(arquivo)}"

    parcela_atual = int(parcela_atual or 0)
    total_parcelas = int(total_parcelas or 0)

    if parcelado:
        if total_parcelas <= 0:
            return None

        if parcela_atual > total_parcelas:
            return None

        valor_parcela = valor
        parcelas_abertas = max(total_parcelas - parcela_atual, 0)
    else:
        parcela_atual = 0
        total_parcelas = 0
        valor_parcela = 0.0
        parcelas_abertas = 0
        tipo_parcela = ""

    return {
        "arquivo_fatura": arquivo,
        "data": data,
        "descricao_original": descricao_limpa,
        "descricao_normalizada": descricao_limpa,
        "valor": float(valor),
        "origem_extracao": origem,
        "parcelado": bool(parcelado),
        "parcela_atual": int(parcela_atual),
        "total_parcelas": int(total_parcelas),
        "parcelas_abertas": int(parcelas_abertas),
        "valor_parcela": float(valor_parcela),
        "tipo_parcela": tipo_parcela,
        "linha_original_pdf": linha_original_pdf or "",
        "confianca_extracao": 95 if origem in ["secao_avista", "secao_parcelada", "secao_anuidade"] else 85,
    }


def extrair_linha_numerica(linha, arquivo, estado=None):
    if linha_bloqueada(linha):
        return None

    m = PADRAO_DATA_VALOR.search(linha.strip())

    if not m:
        return None

    data = m.group("data")
    descricao = m.group("descricao")
    valor = converter_valor(m.group("valor"))
    dc = str(m.group("dc") or "D").upper()

    if dc == "C":
        return None

    parcela_atual, total_parcelas, tipo_parcela = extrair_parcela(descricao)

    if estado == "PARCELADAS" or total_parcelas > 0:
        return montar_item(
            arquivo=arquivo,
            data=data,
            descricao=descricao,
            valor=valor,
            origem="secao_parcelada" if estado == "PARCELADAS" else "data_valor_parcelado",
            parcelado=total_parcelas > 0,
            parcela_atual=parcela_atual,
            total_parcelas=total_parcelas,
            tipo_parcela=tipo_parcela,
            linha_original_pdf=linha,
        )

    return montar_item(
        arquivo=arquivo,
        data=data,
        descricao=descricao,
        valor=valor,
        origem="secao_avista" if estado == "AVISTA" else "data_valor",
        parcelado=False,
        linha_original_pdf=linha,
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
    descricao = m.group("descricao")
    valor = converter_valor(m.group("valor"))
    dc = str(m.group("dc") or "D").upper()

    if dc == "C":
        return None

    return montar_item(
        arquivo=arquivo,
        data=f"{dia}/{mes}/{ano}",
        descricao=descricao,
        valor=valor,
        origem="data_extenso",
        parcelado=False,
        linha_original_pdf=linha,
    )


def extrair_linha_anuidade(linha, arquivo, ano_padrao):
    texto = normalizar_texto(linha)

    if not texto.startswith("ANUIDADE"):
        return None

    m_valor = PADRAO_VALOR.search(texto)

    if not m_valor:
        return None

    return montar_item(
        arquivo=arquivo,
        data=f"01/01/{ano_padrao}",
        descricao=linha,
        valor=m_valor.group(1),
        origem="secao_anuidade",
        parcelado=False,
        linha_original_pdf=linha,
    )


def extrair_transacoes_texto(texto, arquivo_origem=""):
    transacoes = []
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]

    estado = None
    ano = extrair_ano_arquivo(arquivo_origem)

    for linha in linhas:
        novo_estado = detectar_secao(linha, estado)

        if novo_estado != estado:
            estado = novo_estado
            continue

        if linha_bloqueada(linha):
            continue

        item = None

        if estado == "ANUIDADE":
            item = extrair_linha_anuidade(linha, arquivo_origem, ano)

        if item is None:
            item = extrair_linha_numerica(linha, arquivo_origem, estado)

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
    df["descricao_normalizada"] = df["descricao_original"]

    df = df[df["descricao_original"].apply(descricao_valida)]

    df["parcelado"] = df["parcelado"].fillna(False).astype(bool)
    df["parcela_atual"] = pd.to_numeric(df["parcela_atual"], errors="coerce").fillna(0).astype(int)
    df["total_parcelas"] = pd.to_numeric(df["total_parcelas"], errors="coerce").fillna(0).astype(int)
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce").fillna(0).astype(int)
    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0)
    df["confianca_extracao"] = pd.to_numeric(df["confianca_extracao"], errors="coerce").fillna(0).astype(int)

    df = df.drop_duplicates(
        subset=[
            "arquivo_fatura",
            "data",
            "descricao_original",
            "valor",
            "parcelado",
            "parcela_atual",
            "total_parcelas",
        ]
    )

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
