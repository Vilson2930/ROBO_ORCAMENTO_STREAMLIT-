# ============================================================
# TRANSACTION ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

import re
import pandas as pd

# ============================================================
# MAPA DE MESES
# ============================================================

MESES = {
    "jan": "01",
    "fev": "02",
    "mar": "03",
    "abr": "04",
    "mai": "05",
    "jun": "06",
    "jul": "07",
    "ago": "08",
    "set": "09",
    "out": "10",
    "nov": "11",
    "dez": "12",
}

# ============================================================
# PADRÃO DAS TRANSAÇÕES
# Exemplo:
# 28 de mar. 2026 POSTO CALED LTDA - R$ 19,48
# ============================================================

PADRAO_TRANSACAO = re.compile(
    r"(\d{1,2})\s+de\s+([a-zç]{3})\.?\s+(\d{4})\s+(.+?)\s+-\s+R\$\s*([\d\.]+,\d{2})",
    re.IGNORECASE
)

# ============================================================
# EXTRAIR TRANSAÇÕES DE UM TEXTO
# ============================================================

def extrair_transacoes_texto(texto, arquivo_origem=""):

    transacoes = []

    encontrados = PADRAO_TRANSACAO.findall(str(texto))

    for dia, mes_texto, ano, descricao, valor_texto in encontrados:

        mes_texto = mes_texto.lower().replace(".", "")
        mes_numero = MESES.get(mes_texto)

        if not mes_numero:
            continue

        data = f"{dia.zfill(2)}/{mes_numero}/{ano}"

        valor = float(
            valor_texto
            .replace(".", "")
            .replace(",", ".")
        )

        transacoes.append({
            "arquivo_fatura": arquivo_origem,
            "data": data,
            "descricao_original": descricao.strip(),
            "valor": valor
        })

    return transacoes

# ============================================================
# PROCESSAR DOCUMENTOS DO PDF ENGINE
# ============================================================

def processar_transacoes(documentos):

    todas_transacoes = []

    for doc in documentos:

        arquivo = doc.get("arquivo", "")
        texto = doc.get("texto", "")

        transacoes = extrair_transacoes_texto(
            texto,
            arquivo
        )

        todas_transacoes.extend(transacoes)

    df = pd.DataFrame(todas_transacoes)

    if len(df) == 0:
        return df

    df["data"] = pd.to_datetime(
        df["data"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    df = (
        df
        .sort_values(["data", "valor"], ascending=[True, False])
        .reset_index(drop=True)
    )

    return df

# ============================================================
# RESUMO
# ============================================================

def resumo_transacoes(df_transacoes):

    if df_transacoes is None or len(df_transacoes) == 0:
        return {
            "quantidade": 0,
            "valor_total": 0
        }

    return {
        "quantidade": len(df_transacoes),
        "valor_total": float(df_transacoes["valor"].sum())
    }
