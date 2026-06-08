# ============================================================
# TRANSACTION ENGINE
# ORÇAMENTO INTELIGENTE
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

PADROES = [
    re.compile(
        r"(\d{1,2})\s+de\s+([a-zç]+)\.?\s+(\d{4})\s+(.+?)\s+R\$\s*([\d\.]+,\d{2})",
        re.IGNORECASE
    ),
    re.compile(
        r"(\d{2})/(\d{2})/(\d{4})\s+(.+?)\s+R?\$?\s*([\d\.]+,\d{2})",
        re.IGNORECASE
    ),
    re.compile(
        r"(\d{2})/(\d{2})\s+(.+?)\s+R?\$?\s*([\d\.]+,\d{2})",
        re.IGNORECASE
    ),
]


def converter_valor(valor_texto):
    return float(
        str(valor_texto)
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )


def limpar_descricao(descricao):
    descricao = str(descricao).strip()
    descricao = re.sub(r"\s+", " ", descricao)
    descricao = descricao.replace("R$", "").strip()
    return descricao


def extrair_ano_do_arquivo(arquivo_origem):
    m = re.search(r"(20\d{2})", str(arquivo_origem))
    if m:
        return m.group(1)
    return "2026"


def extrair_transacoes_texto(texto, arquivo_origem=""):

    transacoes = []
    texto = str(texto)
    ano_padrao = extrair_ano_do_arquivo(arquivo_origem)

    for padrao in PADROES:

        encontrados = padrao.findall(texto)

        for item in encontrados:

            try:
                if len(item) == 5 and "de" in padrao.pattern:
                    dia, mes_texto, ano, descricao, valor_texto = item
                    mes_texto = mes_texto.lower().replace(".", "")
                    mes_numero = MESES.get(mes_texto)

                    if not mes_numero:
                        continue

                    data = f"{dia.zfill(2)}/{mes_numero}/{ano}"

                elif len(item) == 5:
                    dia, mes, ano, descricao, valor_texto = item
                    data = f"{dia}/{mes}/{ano}"

                elif len(item) == 4:
                    dia, mes, descricao, valor_texto = item
                    data = f"{dia}/{mes}/{ano_padrao}"

                else:
                    continue

                descricao = limpar_descricao(descricao)
                valor = converter_valor(valor_texto)

                if valor <= 0:
                    continue

                if len(descricao) < 3:
                    continue

                transacoes.append({
                    "arquivo_fatura": arquivo_origem,
                    "data": data,
                    "descricao_original": descricao,
                    "valor": valor
                })

            except Exception:
                continue

    return transacoes


def processar_transacoes(documentos):

    todas_transacoes = []

    for doc in documentos:
        arquivo = doc.get("arquivo", "")
        texto = doc.get("texto", "")

        transacoes = extrair_transacoes_texto(
            texto=texto,
            arquivo_origem=arquivo
        )

        todas_transacoes.extend(transacoes)

    df = pd.DataFrame(todas_transacoes)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "arquivo_fatura",
                "data",
                "descricao_original",
                "valor"
            ]
        )

    df["data"] = pd.to_datetime(
        df["data"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    df = df.dropna(subset=["data"])

    df = df.drop_duplicates(
        subset=[
            "arquivo_fatura",
            "data",
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
