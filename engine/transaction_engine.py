# ============================================================
# TRANSACTION ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — bloqueia textos institucionais da fatura
# ============================================================

import re
import pandas as pd

MESES = {
    "jan": "01", "janeiro": "01",
    "fev": "02", "fevereiro": "02",
    "mar": "03", "março": "03", "marco": "03",
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

PADRAO_INTER = re.compile(
    r"(\d{1,2})\s+de\s+([a-zç]+)\.?\s+(\d{4})\s+(.+?)\s+([+-])\s+R\$\s*([\d\.]+,\d{2})",
    re.IGNORECASE
)

PADROES_ALTERNATIVOS = [
    re.compile(
        r"(\d{2})/(\d{2})/(\d{4})\s+(.+?)\s+([+-])?\s*R?\$?\s*([\d\.]+,\d{2})",
        re.IGNORECASE
    ),
    re.compile(
        r"(\d{2})/(\d{2})\s+(.+?)\s+([+-])?\s*R?\$?\s*([\d\.]+,\d{2})",
        re.IGNORECASE
    ),
]

PADRAO_VALOR = re.compile(r"R\$\s*([\d\.]+,\d{2})", re.IGNORECASE)

PADRAO_DATA_EXTENSO = re.compile(
    r"(\d{1,2})\s+de\s+([a-zç]+)\.?\s+(\d{4})",
    re.IGNORECASE
)

PADRAO_DATA_NUMERICA = re.compile(r"(\d{2})/(\d{2})(?:/(\d{4}))?")

PADRAO_PARCELA = re.compile(
    r"(PARCELA\s*\d{1,2}\s*DE\s*\d{1,2}|PARC\s*\d{1,2}\s*/\s*\d{1,2}|\b\d{1,2}\s*/\s*\d{1,2}\b|\b\d{1,2}\s*X\b)",
    re.IGNORECASE
)

TERMOS_INSTITUCIONAIS = [
    "FATURA ATUAL",
    "DESPESAS DO MES",
    "DESPESAS DO MÊS",
    "DESPESAS DA FATURA",
    "TOTAL DA SUA FATURA",
    "VALOR TOTAL DA FATURA",
    "PAGAMENTO TOTAL",
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "PAGAMENTO PARCIAL",
    "PRECISA DE UMA FORCA",
    "PRECISA DE UMA FORÇA",
    "VALOR TOTAL FINANCIADO",
    "VALOR FINANCIADO",
    "SALDO FINANCIADO",
    "SALDO DEVEDOR",
    "SALDO QUE PODE VIRAR ROTATIVO",
    "CREDITO ROTATIVO",
    "CRÉDITO ROTATIVO",
    "ROTATIVO",
    "ENCARGOS",
    "ENCARGOS FINANCEIROS",
    "ENCARGOS ROTATIVOS",
    "JUROS",
    "JUROS ROTATIVO",
    "IOF",
    "IOF DIARIO",
    "IOF DIÁRIO",
    "IOF ADICIONAL",
    "TAXA EFETIVA",
    "TAXA EFETIVA MENSAL",
    "TAXA EFETIVA ANUAL",
    "CET",
    "MULTA",
    "MORA",
    "LIMITE DE CREDITO",
    "LIMITE DE CRÉDITO",
    "PONTOS LOOP",
    "SALDO TOTAL",
    "VENCIMENTO",
    "FECHAMENTO",
    "RESUMO DA FATURA",
    "SIMULACAO",
    "SIMULAÇÃO",
    "SIMULADO",
    "OBSERVACAO",
    "OBSERVAÇÃO",
]

TERMOS_CREDITO_PAGAMENTO = [
    "PAGAMENTO ON LINE",
    "PAGAMENTO ONLINE",
    "PAGAMENTO VIA",
    "PAGAMENTO PIX",
    "PAGAMENTO BOLETO",
    "VALOR ANTECIPADO",
    "CREDITO DE PAGAMENTO",
    "CRÉDITO DE PAGAMENTO",
    "ESTORNO",
    "CREDITO",
    "CRÉDITO",
]


def normalizar(texto):
    texto = str(texto or "")
    texto = texto.replace("\r", "\n").replace("\t", " ")
    texto = re.sub(r"[ ]+", " ", texto)
    return texto.strip()


def normalizar_busca(texto):
    texto = str(texto or "").upper()

    trocas = {
        "Á": "A", "À": "A", "Ã": "A", "Â": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Õ": "O", "Ô": "O",
        "Ú": "U",
        "Ç": "C",
    }

    for a, b in trocas.items():
        texto = texto.replace(a, b)

    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def converter_valor(valor_texto):
    return float(str(valor_texto).replace(".", "").replace(",", ".").strip())


def limpar_descricao(descricao):
    descricao = normalizar(descricao)
    descricao = descricao.replace("R$", "").strip()
    descricao = descricao.replace(" - ", " ").strip()
    descricao = re.sub(r"\s+", " ", descricao)
    return descricao.strip(" -")


def extrair_ano_do_arquivo(arquivo_origem):
    m = re.search(r"(20\d{2})", str(arquivo_origem))
    return m.group(1) if m else "2026"


def extrair_mes_do_arquivo(arquivo_origem):
    texto = str(arquivo_origem).lower()
    for nome_mes, numero in MESES.items():
        if nome_mes in texto:
            return numero
    return "06"


def montar_data_padrao(arquivo_origem):
    return f"01/{extrair_mes_do_arquivo(arquivo_origem)}/{extrair_ano_do_arquivo(arquivo_origem)}"


def eh_linha_institucional(descricao):
    texto = normalizar_busca(descricao)

    if not texto:
        return True

    for termo in TERMOS_INSTITUCIONAIS:
        if normalizar_busca(termo) in texto:
            return True

    return False


def eh_credito_ou_pagamento_real(descricao, sinal):
    texto = normalizar_busca(descricao)

    if sinal == "+":
        return True

    for termo in TERMOS_CREDITO_PAGAMENTO:
        if normalizar_busca(termo) in texto:
            return True

    return False


def descricao_parece_compra_real(descricao):
    texto = normalizar_busca(descricao)

    if len(texto) < 3:
        return False

    if eh_linha_institucional(texto):
        return False

    if len(texto) > 140:
        return False

    if texto.count("/") > 5:
        return False

    if texto.count("*") > 8:
        return False

    if re.search(r"\b\d{4}\*{2,}\d{4}\b", texto):
        return False

    if "VILSON JOSE PEREIRA PINTO" in texto:
        return False

    return True


def contem_parcelamento_real(texto):
    texto = str(texto or "")
    texto_norm = normalizar_busca(texto)

    if eh_linha_institucional(texto_norm):
        return False

    return bool(PADRAO_PARCELA.search(texto_norm))


def extrair_transacoes_inter(texto, arquivo_origem):
    transacoes = []

    for dia, mes_texto, ano, descricao, sinal, valor_texto in PADRAO_INTER.findall(texto):
        try:
            descricao = limpar_descricao(descricao)

            if eh_credito_ou_pagamento_real(descricao, sinal):
                continue

            if not descricao_parece_compra_real(descricao):
                continue

            mes_texto = mes_texto.lower().replace(".", "")
            mes_numero = MESES.get(mes_texto)

            if not mes_numero:
                continue

            valor = converter_valor(valor_texto)

            if valor <= 0:
                continue

            transacoes.append({
                "arquivo_fatura": arquivo_origem,
                "data": f"{dia.zfill(2)}/{mes_numero}/{ano}",
                "descricao_original": descricao,
                "valor": valor,
                "origem_extracao": "padrao_inter"
            })

        except Exception:
            continue

    return transacoes


def extrair_transacoes_alternativas(texto, arquivo_origem):
    transacoes = []
    ano_padrao = extrair_ano_do_arquivo(arquivo_origem)

    for padrao in PADROES_ALTERNATIVOS:
        for item in padrao.findall(texto):
            try:
                if len(item) == 6:
                    dia, mes, ano, descricao, sinal, valor_texto = item
                    data = f"{dia}/{mes}/{ano}"
                elif len(item) == 5:
                    dia, mes, descricao, sinal, valor_texto = item
                    data = f"{dia}/{mes}/{ano_padrao}"
                else:
                    continue

                descricao = limpar_descricao(descricao)

                if eh_credito_ou_pagamento_real(descricao, sinal):
                    continue

                if not descricao_parece_compra_real(descricao):
                    continue

                valor = converter_valor(valor_texto)

                if valor <= 0:
                    continue

                transacoes.append({
                    "arquivo_fatura": arquivo_origem,
                    "data": data,
                    "descricao_original": descricao,
                    "valor": valor,
                    "origem_extracao": "padrao_alternativo"
                })

            except Exception:
                continue

    return transacoes


def extrair_transacoes_sem_data(texto, arquivo_origem=""):
    transacoes = []
    linhas = [l.strip() for l in str(texto).splitlines() if l.strip()]
    data_padrao = montar_data_padrao(arquivo_origem)

    for linha in linhas:
        linha_limpa = limpar_descricao(linha)

        if not linha_limpa:
            continue

        if eh_linha_institucional(linha_limpa):
            continue

        if "R$" not in linha_limpa.upper():
            continue

        valores = PADRAO_VALOR.findall(linha_limpa)

        if not valores:
            continue

        try:
            valor_texto = valores[-1]
            valor = converter_valor(valor_texto)

            descricao = PADRAO_VALOR.sub("", linha_limpa).strip()
            descricao = limpar_descricao(descricao)

            if not descricao_parece_compra_real(descricao):
                continue

            if valor <= 0:
                continue

            transacoes.append({
                "arquivo_fatura": arquivo_origem,
                "data": data_padrao,
                "descricao_original": descricao,
                "valor": valor,
                "origem_extracao": "sem_data"
            })

        except Exception:
            continue

    return transacoes


def preservar_linhas_criticas(texto, arquivo_origem=""):
    """
    Preserva apenas parcelamentos reais.
    Não preserva juros, IOF, rotativo, pagamento mínimo ou textos institucionais.
    """

    transacoes = []
    linhas = [l.strip() for l in str(texto).splitlines() if l.strip()]
    data_padrao = montar_data_padrao(arquivo_origem)

    for linha in linhas:
        linha_limpa = limpar_descricao(linha)

        if not contem_parcelamento_real(linha_limpa):
            continue

        if eh_linha_institucional(linha_limpa):
            continue

        valores = PADRAO_VALOR.findall(linha_limpa)

        if not valores:
            continue

        try:
            valor = converter_valor(valores[-1])
            descricao = PADRAO_VALOR.sub("", linha_limpa)
            descricao = limpar_descricao(descricao)

            if not descricao_parece_compra_real(descricao):
                continue

            if valor <= 0:
                continue

            transacoes.append({
                "arquivo_fatura": arquivo_origem,
                "data": data_padrao,
                "descricao_original": descricao,
                "valor": valor,
                "origem_extracao": "parcelamento_real"
            })

        except Exception:
            continue

    return transacoes


def extrair_transacoes_texto(texto, arquivo_origem=""):
    texto = normalizar(texto)

    transacoes = []
    transacoes.extend(extrair_transacoes_inter(texto, arquivo_origem))
    transacoes.extend(extrair_transacoes_alternativas(texto, arquivo_origem))
    transacoes.extend(extrair_transacoes_sem_data(texto, arquivo_origem))
    transacoes.extend(preservar_linhas_criticas(texto, arquivo_origem))

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

    df = pd.DataFrame(todas)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "arquivo_fatura",
                "data",
                "descricao_original",
                "valor",
                "origem_extracao"
            ]
        )

    df["data"] = pd.to_datetime(
        df["data"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    df = df.dropna(subset=["data"])

    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    df = df[df["valor"] > 0]

    df["descricao_original"] = df["descricao_original"].apply(limpar_descricao)

    df = df[
        df["descricao_original"].apply(descricao_parece_compra_real)
    ].copy()

    df = df.drop_duplicates(
        subset=[
            "arquivo_fatura",
            "descricao_original",
            "valor"
        ]
    )

    df = df.sort_values(
        ["data", "valor"],
        ascending=[True, False]
    ).reset_index(drop=True)

    return df


def resumo_transacoes(df_transacoes):
    if df_transacoes is None or df_transacoes.empty:
        return {
            "quantidade": 0,
            "valor_total": 0
        }

    return {
        "quantidade": len(df_transacoes),
        "valor_total": float(df_transacoes["valor"].sum())
    }
