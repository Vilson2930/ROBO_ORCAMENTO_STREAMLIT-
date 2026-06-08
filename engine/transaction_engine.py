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


def eh_linha_ignorada(descricao):
    texto = str(descricao).upper()

    termos_ignorar = [
        "PAGAMENTO ON LINE",
        "PAGAMENTO ONLINE",
        "PAGAMENTO VIA",
        "VALOR ANTECIPADO",
        "FATURA ATUAL",
        "DESPESAS DO MES",
        "DESPESAS DO MÊS",
        "TOTAL DA SUA FATURA",
        "PAGAMENTO MINIMO",
        "PAGAMENTO MÍNIMO",
        "ENCARGOS",
        "IOF",
        "PARCELAMENTO TOTAL",
        "LIMITE DE CREDITO",
        "LIMITE DE CRÉDITO",
        "BOLETO",
        "PIX",
        "PONTOS LOOP",
    ]

    return any(t in texto for t in termos_ignorar)


def extrair_transacoes_texto(texto, arquivo_origem=""):

    transacoes = []
    texto = str(texto)
    ano_padrao = extrair_ano_do_arquivo(arquivo_origem)

    # --------------------------------------------------------
    # PADRÃO PRINCIPAL — FATURA INTER
    # Exemplo:
    # 03 de dez. 2025 PAGAMENTO ON LINE - + R$ 6.950,82
    # 10 de dez. 2025 SUPERMERCADO SUPERPAO - R$ 85,89
    # --------------------------------------------------------

    encontrados = PADRAO_INTER.findall(texto)

    for dia, mes_texto, ano, descricao, sinal, valor_texto in encontrados:

        try:
            # Crédito / pagamento / estorno: ignorar
            if sinal == "+":
                continue

            descricao = limpar_descricao(descricao)

            if eh_linha_ignorada(descricao):
                continue

            mes_texto = mes_texto.lower().replace(".", "")
            mes_numero = MESES.get(mes_texto)

            if not mes_numero:
                continue

            data = f"{dia.zfill(2)}/{mes_numero}/{ano}"
            valor = converter_valor(valor_texto)

            if valor <= 0 or len(descricao) < 3:
                continue

            transacoes.append({
                "arquivo_fatura": arquivo_origem,
                "data": data,
                "descricao_original": descricao,
                "valor": valor
            })

        except Exception:
            continue

    # Se encontrou transações no padrão Inter, não precisa usar padrões alternativos
    if transacoes:
        return transacoes

    # --------------------------------------------------------
    # PADRÕES ALTERNATIVOS
    # --------------------------------------------------------

    for padrao in PADROES_ALTERNATIVOS:

        encontrados = padrao.findall(texto)

        for item in encontrados:

            try:
                if len(item) == 6:
                    dia, mes, ano, descricao, sinal, valor_texto = item
                    data = f"{dia}/{mes}/{ano}"

                elif len(item) == 5:
                    dia, mes, descricao, sinal, valor_texto = item
                    data = f"{dia}/{mes}/{ano_padrao}"

                else:
                    continue

                if sinal == "+":
                    continue

                descricao = limpar_descricao(descricao)

                if eh_linha_ignorada(descricao):
                    continue

                valor = converter_valor(valor_texto)

                if valor <= 0 or len(descricao) < 3:
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
