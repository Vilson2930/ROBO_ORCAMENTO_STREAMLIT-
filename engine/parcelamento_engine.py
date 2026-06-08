# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

import re
import pandas as pd

# ============================================================
# EXTRAIR PARCELA
# ============================================================

def extrair_parcela(texto):

    texto = str(texto).upper()

    padrao = re.search(
        r"PARCELA\s*(\d+)\s*DE\s*(\d+)",
        texto
    )

    if padrao:

        atual = int(padrao.group(1))
        total = int(padrao.group(2))

        return atual, total

    return None, None


# ============================================================
# LIMPAR NOME DA COMPRA
# ============================================================

def limpar_compra(texto):

    texto = str(texto).upper()

    texto = re.sub(
        r"\(PARCELA\s*\d+\s*DE\s*\d+\)",
        "",
        texto
    )

    texto = re.sub(
        r"PARCELA\s*\d+\s*DE\s*\d+",
        "",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


# ============================================================
# PROCESSAR PARCELAMENTOS
# ============================================================

def processar_parcelamentos(df):

    if len(df) == 0:
        return pd.DataFrame()

    temp = df.copy()

    temp["compra"] = temp[
        "descricao_original"
    ].apply(
        limpar_compra
    )

    temp["parcela_atual"] = temp[
        "descricao_original"
    ].apply(
        lambda x: extrair_parcela(x)[0]
    )

    temp["total_parcelas"] = temp[
        "descricao_original"
    ].apply(
        lambda x: extrair_parcela(x)[1]
    )

    parcelados = temp[
        temp["parcela_atual"].notna()
    ].copy()

    if len(parcelados) == 0:
        return pd.DataFrame()

    resultado = []

    for compra, grupo in parcelados.groupby("compra"):

        ultima_parcela = int(
            grupo["parcela_atual"].max()
        )

        total_parcelas = int(
            grupo["total_parcelas"].max()
        )

        linha = grupo[
            grupo["parcela_atual"] == ultima_parcela
        ].iloc[-1]

        valor_parcela = float(
            linha["valor"]
        )

        parcelas_abertas = max(
            total_parcelas - ultima_parcela,
            0
        )

        valor_total_compra = (
            total_parcelas *
            valor_parcela
        )

        valor_pago = (
            ultima_parcela *
            valor_parcela
        )

        valor_restante = (
            parcelas_abertas *
            valor_parcela
        )

        status = (
            "QUITADO"
            if parcelas_abertas == 0
            else "ABERTO"
        )

        resultado.append({

            "compra":
                compra,

            "categoria":
                linha.get(
                    "categoria",
                    "Outros"
                ),

            "ultima_parcela":
                ultima_parcela,

            "total_parcelas":
                total_parcelas,

            "parcelas_pagas":
                ultima_parcela,

            "parcelas_abertas":
                parcelas_abertas,

            "valor_parcela":
                valor_parcela,

            "valor_total_compra":
                valor_total_compra,

            "valor_pago":
                valor_pago,

            "valor_restante":
                valor_restante,

            "status":
                status

        })

    resultado = pd.DataFrame(resultado)

    resultado = resultado.sort_values(
        "valor_restante",
        ascending=False
    )

    return resultado


# ============================================================
# RESUMO EXECUTIVO
# ============================================================

def resumo_parcelamentos(df_parcelamentos):

    if len(df_parcelamentos) == 0:

        return {

            "parcelamentos": 0,
            "abertos": 0,
            "quitados": 0,
            "valor_restante": 0

        }

    return {

        "parcelamentos":
            len(df_parcelamentos),

        "abertos":
            len(
                df_parcelamentos[
                    df_parcelamentos["status"]
                    == "ABERTO"
                ]
            ),

        "quitados":
            len(
                df_parcelamentos[
                    df_parcelamentos["status"]
                    == "QUITADO"
                ]
            ),

        "valor_restante":
            float(
                df_parcelamentos[
                    "valor_restante"
                ].sum()
            )

    }
