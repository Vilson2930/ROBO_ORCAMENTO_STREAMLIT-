# ============================================================
# TRANSACTION ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — reconhece somente débitos reais de fatura
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
    "PRECISA DE UMA FORCA", "PRECISA DE UMA FORÇA",
    "ENCARGOS FINANCEIROS", "ENCARGOS", "ROTATIVO",
    "TOTAL DA FATURA", "VALOR TOTAL DA FATURA", "TOTAL A PAGAR",
    "LIMITE", "VENCIMENTO", "FECHAMENTO", "MELHOR DIA",
    "PAGINA", "PÁGINA", "RESUMO", "FATURA",
    "VILSON JOSE PEREIRA PINTO", "5364", "4593",
    "IOF", "JUROS", "MULTA", "MORA", "CET",
    "SALDO", "CREDITO", "CRÉDITO", "ESTORNO",
]

PADRAO_DATA_VALOR = re.compile(
    r"(?P<data>\d{2}/\d{2}(?:/\d{4})?)\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})$",
    re.IGNORECASE
)

PADRAO_EXTENSO_VALOR = re.compile(
    r"(?P<dia>\d{1,2})\s+DE\s+(?P<mes>[A-ZÇ]+)\.?\s+(?P<ano>\d{4})\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})$",
    re.IGNORECASE
)


def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def limpar_descricao(descricao):
    descricao = str(descricao or "")
    descricao = re.sub(r"R\$", "", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"\s+", " ", descricao)
    return descricao.strip(" -")


def converter_valor(valor):
    return float(str(valor).replace(".", "").replace(",", "."))


def extrair_ano_arquivo(nome_arquivo):
    m = re.search(r"(20\d{2})", str(nome_arquivo))
    return m.group(1) if m else "2026"


def linha_bloqueada(linha):
    texto = normalizar_texto(linha)

    if not texto:
        return True

    for termo in BLACKLIST:
        if normalizar_texto(termo) in texto:
            return True

    if len(texto) > 120:
        return True

    if texto.count("*") >= 4:
        return True

    if texto.count("/") > 4:
        return True

    return False


def descricao_valida(descricao):
    texto = normalizar_texto(descricao)

    if linha_bloqueada(texto):
        return False

    if len(texto) < 3:
        return False

    if len(texto) > 80:
        return False

    if not re.search(r"[A-Z]", texto):
        return False

    return True


def extrair_linha_numerica(linha, arquivo):
    m = PADRAO_DATA_VALOR.search(linha.strip())
    if not m:
        return None

    data = m.group("data")
    descricao = limpar_descricao(m.group("descricao"))
    valor = converter_valor(m.group("valor"))

    if len(data) == 5:
        data = f"{data}/{extrair_ano_arquivo(arquivo)}"

    if valor <= 0:
        return None

    if not descricao_valida(descricao):
        return None

    return {
        "arquivo_fatura": arquivo,
        "data": data,
        "descricao_original": descricao,
        "valor": valor,
        "origem_extracao": "data_valor"
    }


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
    descricao = limpar_descricao(m.group("descricao"))
    valor = converter_valor(m.group("valor"))

    if valor <= 0:
        return None

    if not descricao_valida(descricao):
        return None

    return {
        "arquivo_fatura": arquivo,
        "data": f"{dia}/{mes}/{ano}",
        "descricao_original": descricao,
        "valor": valor,
        "origem_extracao": "data_extenso"
    }


def extrair_transacoes_texto(texto, arquivo_origem=""):
    transacoes = []

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
        "valor",
        "origem_extracao"
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
    df = df[df["descricao_original"].apply(descricao_valida)]

    df = df.drop_duplicates(
        subset=["arquivo_fatura", "data", "descricao_original", "valor"]
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
