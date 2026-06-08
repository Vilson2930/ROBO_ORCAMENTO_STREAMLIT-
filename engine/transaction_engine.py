# ============================================================
# TRANSACTION ENGINE
# ORÇAMENTO INTELIGENTE
# Versão robusta — preserva parcelamentos, dívida, PIX, boleto e encargos
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

TERMOS_DIVIDA = [
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "PAGAMENTO PARCIAL",
    "SALDO FINANCIADO",
    "SALDO DEVEDOR",
    "CREDITO ROTATIVO",
    "CRÉDITO ROTATIVO",
    "JUROS ROTATIVO",
    "JUROS",
    "IOF",
    "MULTA",
    "ENCARGOS",
    "ENCARGOS FINANCEIROS",
    "PARCELAMENTO FATURA",
    "PARCELAMENTO DE FATURA",
]


def normalizar(texto):
    texto = str(texto or "")
    texto = texto.replace("\r", "\n").replace("\t", " ")
    texto = re.sub(r"[ ]+", " ", texto)
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


def eh_linha_ignorada(descricao):
    texto = str(descricao).upper()

    termos_ignorar = [
        "FATURA ATUAL",
        "DESPESAS DO MES",
        "DESPESAS DO MÊS",
        "TOTAL DA SUA FATURA",
        "VALOR TOTAL DA FATURA",
        "LIMITE DE CREDITO",
        "LIMITE DE CRÉDITO",
        "PONTOS LOOP",
        "SALDO TOTAL",
        "VENCIMENTO",
        "FECHAMENTO",
        "RESUMO DA FATURA",
    ]

    return any(t in texto for t in termos_ignorar)


def eh_credito_ou_pagamento_real(descricao, sinal):
    texto = str(descricao).upper()

    if sinal == "+":
        return True

    ignorar = [
        "PAGAMENTO ON LINE",
        "PAGAMENTO ONLINE",
        "PAGAMENTO VIA",
        "VALOR ANTECIPADO",
        "CREDITO DE PAGAMENTO",
        "CRÉDITO DE PAGAMENTO",
        "ESTORNO",
    ]

    return any(t in texto for t in ignorar)


def contem_parcela_ou_divida(texto):
    t = str(texto).upper()

    if PADRAO_PARCELA.search(t):
        return True

    return any(term.upper() in t for term in TERMOS_DIVIDA)


def extrair_transacoes_inter(texto, arquivo_origem):
    transacoes = []

    for dia, mes_texto, ano, descricao, sinal, valor_texto in PADRAO_INTER.findall(texto):
        try:
            descricao = limpar_descricao(descricao)

            if eh_credito_ou_pagamento_real(descricao, sinal):
                continue

            if eh_linha_ignorada(descricao):
                continue

            mes_texto = mes_texto.lower().replace(".", "")
            mes_numero = MESES.get(mes_texto)

            if not mes_numero:
                continue

            valor = converter_valor(valor_texto)

            if valor <= 0 or len(descricao) < 3:
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

                if eh_linha_ignorada(descricao):
                    continue

                valor = converter_valor(valor_texto)

                if valor <= 0 or len(descricao) < 3:
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

    buffer = []

    for linha in linhas:
        linha_limpa = limpar_descricao(linha)

        if not linha_limpa:
            continue

        if "R$" in linha_limpa.upper():
            valores = PADRAO_VALOR.findall(linha_limpa)

            if not valores:
                continue

            valor_texto = valores[-1]
            valor = converter_valor(valor_texto)

            descricao_linha = PADRAO_VALOR.sub("", linha_limpa).strip()
            partes = buffer.copy()

            if descricao_linha:
                partes.append(descricao_linha)

            descricao = limpar_descricao(" ".join(partes))
            buffer = []

            if not descricao or len(descricao) < 3:
                continue

            if eh_linha_ignorada(descricao):
                continue

            transacoes.append({
                "arquivo_fatura": arquivo_origem,
                "data": data_padrao,
                "descricao_original": descricao,
                "valor": valor,
                "origem_extracao": "sem_data"
            })

        else:
            if not PADRAO_DATA_NUMERICA.search(linha_limpa) and not PADRAO_DATA_EXTENSO.search(linha_limpa):
                buffer.append(linha_limpa)

    return transacoes


def preservar_linhas_criticas(texto, arquivo_origem=""):
    """
    Captura especificamente linhas com parcelamento ou dívida que podem ter sido
    perdidas nos padrões principais.
    """

    transacoes = []
    linhas = [l.strip() for l in str(texto).splitlines() if l.strip()]
    data_padrao = montar_data_padrao(arquivo_origem)

    for i, linha in enumerate(linhas):
        contexto = " ".join(linhas[max(0, i - 2): min(len(linhas), i + 3)])

        if not contem_parcela_ou_divida(contexto):
            continue

        valores = PADRAO_VALOR.findall(contexto)

        if not valores:
            continue

        try:
            valor = converter_valor(valores[-1])
            descricao = PADRAO_VALOR.sub("", contexto)
            descricao = limpar_descricao(descricao)

            if not descricao or len(descricao) < 3:
                continue

            if eh_linha_ignorada(descricao):
                continue

            transacoes.append({
                "arquivo_fatura": arquivo_origem,
                "data": data_padrao,
                "descricao_original": descricao,
                "valor": valor,
                "origem_extracao": "linha_critica"
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
