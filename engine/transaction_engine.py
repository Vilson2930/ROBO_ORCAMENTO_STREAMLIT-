# ============================================================
# TRANSACTION ENGINE
# ORÇAMENTO INTELIGENTE
# Débitos reais + compras parceladas em bloco
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
    "PRECISA DE UMA FORCA", "PRECISA DE UMA FORÇA",
    "ENCARGOS FINANCEIROS", "ENCARGOS", "ROTATIVO",
    "TOTAL DA FATURA", "VALOR TOTAL DA FATURA", "TOTAL A PAGAR",
    "LIMITE", "VENCIMENTO", "FECHAMENTO", "MELHOR DIA",
    "PAGINA", "PÁGINA", "RESUMO", "FATURA",
    "VILSON JOSE PEREIRA PINTO", "5364", "4593",
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

PADRAO_VALOR = re.compile(r"R\$\s*([\d\.]+,\d{2})", re.IGNORECASE)

PADRAO_NX_DE = re.compile(
    r"(?P<qtd>\d{1,2})\s*X\s*DE\s*R\$\s*(?P<valor>[\d\.]+,\d{2})",
    re.IGNORECASE
)

PADRAO_DATA_CURTA = re.compile(r"\b\d{2}/\d{2}(?:/\d{4})?\b")


def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def limpar_descricao(descricao):
    descricao = str(descricao or "")
    descricao = re.sub(r"R\$\s*[\d\.]+,\d{2}", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"\d{1,2}\s*X\s*DE\s*R?\$?\s*[\d\.]+,\d{2}", " ", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"\b\d{2}/\d{2}(?:/\d{4})?\b", " ", descricao)
    descricao = re.sub(r"R\$", "", descricao, flags=re.IGNORECASE)
    descricao = re.sub(r"[*]+", " ", descricao)
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

    if "PAGAMENTO" in texto:
        return True

    if "BOLETO" in texto or "PIX" in texto:
        return True

    if texto.endswith("+"):
        return True

    if " - +" in texto or "+ R$" in texto or " + " in texto:
        return True

    if len(texto) > 160:
        return True

    if texto.count("*") >= 8:
        return True

    return False


def descricao_valida(descricao):
    texto = normalizar_texto(descricao)

    if linha_bloqueada(texto):
        return False

    if len(texto) < 3:
        return False

    if len(texto) > 100:
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
        "origem_extracao": "data_valor",
        "parcelado": False,
        "parcelas_abertas": 0,
        "valor_parcela": 0.0
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
        "origem_extracao": "data_extenso",
        "parcelado": False,
        "parcelas_abertas": 0,
        "valor_parcela": 0.0
    }


def extrair_compras_parceladas_em_bloco(texto, arquivo_origem=""):
    """
    Captura bloco universal de fatura:
    LOJA
    CIDADE / UF
    DATA
    R$ TOTAL
    Nx de R$ VALOR
    """

    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    transacoes = []

    contexto = []
    valor_total = None
    data_detectada = None

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if linha_norm.startswith("--- PAGINA"):
            contexto = []
            valor_total = None
            data_detectada = None
            continue

        data_m = PADRAO_DATA_CURTA.search(linha_norm)
        if data_m:
            data_detectada = data_m.group(0)
            if len(data_detectada) == 5:
                data_detectada = f"{data_detectada}/{extrair_ano_arquivo(arquivo_origem)}"

        valores = PADRAO_VALOR.findall(linha_norm)
        if valores:
            valor_total = converter_valor(valores[0])
            sem_valor = PADRAO_VALOR.sub(" ", linha_norm)
            sem_valor = limpar_descricao(sem_valor)
            if sem_valor and not linha_bloqueada(sem_valor):
                contexto.append(sem_valor)

        m = PADRAO_NX_DE.search(linha_norm)
        if m:
            parcelas_abertas = int(m.group("qtd"))
            valor_parcela = converter_valor(m.group("valor"))

            if valor_total is None:
                valor_total = round(parcelas_abertas * valor_parcela, 2)

            descricao = limpar_descricao(" ".join(contexto[-4:]))

            if not descricao:
                descricao = "COMPRA PARCELADA"

            if descricao_valida(descricao):
                transacoes.append({
                    "arquivo_fatura": arquivo_origem,
                    "data": data_detectada or f"01/01/{extrair_ano_arquivo(arquivo_origem)}",
                    "descricao_original": descricao,
                    "valor": float(valor_total),
                    "origem_extracao": "parcelamento_bloco",
                    "parcelado": True,
                    "parcelas_abertas": int(parcelas_abertas),
                    "valor_parcela": float(valor_parcela)
                })

            contexto = []
            valor_total = None
            data_detectada = None
            continue

        if not valores and len(linha_norm) >= 3 and not linha_bloqueada(linha_norm):
            contexto.append(linha_norm)
            contexto = contexto[-5:]

    return transacoes


def extrair_transacoes_texto(texto, arquivo_origem=""):
    transacoes = []

    transacoes.extend(
        extrair_compras_parceladas_em_bloco(
            texto=texto,
            arquivo_origem=arquivo_origem
        )
    )

    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]

    for linha in linhas:
        if linha_bloqueada(linha):
            continue

        if PADRAO_NX_DE.search(linha):
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
        "origem_extracao",
        "parcelado",
        "parcelas_abertas",
        "valor_parcela"
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

    df["parcelado"] = df["parcelado"].fillna(False)
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce").fillna(0).astype(int)
    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0)

    df = df.drop_duplicates(
        subset=[
            "arquivo_fatura",
            "data",
            "descricao_original",
            "valor",
            "parcelado",
            "parcelas_abertas",
            "valor_parcela"
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
