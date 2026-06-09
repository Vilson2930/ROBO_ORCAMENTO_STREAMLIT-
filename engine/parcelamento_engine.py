# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — explícitos + prováveis com saldo conservador
# ============================================================

import re
import pandas as pd
import unicodedata


def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


TERMOS_BLOQUEADOS = [
    "PAGAMENTO", "PIX", "BOLETO", "ESTORNO", "CREDITO",
    "JUROS", "IOF", "ENCARGOS", "ROTATIVO", "SALDO",
    "TOTAL DA FATURA", "DESPESAS DA FATURA", "FATURA",
]


PADROES_PARCELA = [
    r"\bPARCELA\s*(\d{1,2})\s*DE\s*(\d{1,2})\b",
    r"\bPARC(?:ELA)?\.?\s*(\d{1,2})\s*/\s*(\d{1,2})\b",
    r"\bPARC(?:ELA)?\.?\s*(\d{1,2})\s*DE\s*(\d{1,2})\b",
    r"\bCOMPRA\s*PARCELADA\s*(\d{1,2})\s*/\s*(\d{1,2})\b",
    r"\bPARCELADO\s*(\d{1,2})\s*/\s*(\d{1,2})\b",
    r"\b(\d{1,2})\s*/\s*(\d{1,2})\b",
]

PADRAO_X = re.compile(r"\b(\d{1,2})\s*X\b", re.IGNORECASE)


def contem_bloqueado(texto):
    texto = normalizar_texto(texto)
    return any(t in texto for t in TERMOS_BLOQUEADOS)


def extrair_parcela(texto):
    texto = normalizar_texto(texto)

    if not texto or contem_bloqueado(texto):
        return None, None

    for padrao in PADROES_PARCELA:
        m = re.search(padrao, texto)
        if m:
            atual = int(m.group(1))
            total = int(m.group(2))
            if 1 <= atual <= total and 2 <= total <= 60:
                return atual, total

    m = PADRAO_X.search(texto)
    if m:
        total = int(m.group(1))
        if 2 <= total <= 60:
            return 1, total

    return None, None


def limpar_compra(texto):
    texto = normalizar_texto(texto)

    limpezas = [
        r"\bPARCELA\s*\d{1,2}\s*DE\s*\d{1,2}\b",
        r"\bPARC(?:ELA)?\.?\s*\d{1,2}\s*/\s*\d{1,2}\b",
        r"\bPARC(?:ELA)?\.?\s*\d{1,2}\s*DE\s*\d{1,2}\b",
        r"\bCOMPRA\s*PARCELADA\s*\d{1,2}\s*/\s*\d{1,2}\b",
        r"\bPARCELADO\s*\d{1,2}\s*/\s*\d{1,2}\b",
        r"\b\d{1,2}\s*/\s*\d{1,2}\b",
        r"\b\d{1,2}\s*X\b",
        r"COMPRA PARCELADA",
        r"PARCELADO",
        r"PARCELAMENTO",
    ]

    for padrao in limpezas:
        texto = re.sub(padrao, "", texto)

    texto = re.sub(r"\(\s*\)", "", texto)
    texto = re.sub(r"[*]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip(" -")


def encontrar_coluna_descricao(df):
    for col in ["descricao_original", "descricao", "merchant", "estabelecimento", "compra", "texto", "lancamento"]:
        if col in df.columns:
            return col

    for col in df.columns:
        if df[col].dtype == "object":
            return col

    return None


def encontrar_coluna_valor(df):
    for col in ["valor", "valor_total", "total", "amount", "gasto"]:
        if col in df.columns:
            return col

    numericas = df.select_dtypes(include="number").columns.tolist()
    return numericas[0] if numericas else None


def criar_item(compra, categoria, parcela_atual, total_parcelas, valor_parcela, descricao, tipo):
    parcelas_abertas = max(total_parcelas - parcela_atual, 0)

    return {
        "compra": compra,
        "categoria": categoria,
        "ultima_parcela": int(parcela_atual),
        "total_parcelas": int(total_parcelas),
        "parcelas_pagas": int(parcela_atual),
        "parcelas_abertas": int(parcelas_abertas),
        "valor_parcela": float(valor_parcela),
        "valor_total_compra": float(total_parcelas * valor_parcela),
        "valor_pago": float(parcela_atual * valor_parcela),
        "valor_restante": float(parcelas_abertas * valor_parcela),
        "status": "QUITADO" if parcelas_abertas == 0 else "ABERTO",
        "tipo_detectado": tipo,
        "descricao_detectada": descricao,
    }


def detectar_explicitos(temp, coluna_desc, coluna_valor):
    resultado = []

    for _, linha in temp.iterrows():
        descricao = str(linha.get(coluna_desc, ""))
        valor = float(linha.get(coluna_valor, 0))

        if valor <= 0 or contem_bloqueado(descricao):
            continue

        parcela_atual, total_parcelas = extrair_parcela(descricao)

        if parcela_atual is None:
            continue

        compra = limpar_compra(descricao)

        if not compra or contem_bloqueado(compra):
            continue

        resultado.append(
            criar_item(
                compra=compra,
                categoria=linha.get("categoria", "Outros"),
                parcela_atual=parcela_atual,
                total_parcelas=total_parcelas,
                valor_parcela=valor,
                descricao=descricao,
                tipo="EXPLICITO",
            )
        )

    return resultado


def detectar_provaveis(temp, coluna_desc, coluna_valor):
    resultado = []

    temp = temp.copy()
    temp["compra_limpa"] = temp[coluna_desc].apply(limpar_compra)
    temp["valor_parcela_base"] = pd.to_numeric(temp[coluna_valor], errors="coerce").round(2)

    temp = temp[temp["valor_parcela_base"] > 0]
    temp = temp[~temp["compra_limpa"].apply(contem_bloqueado)]
    temp = temp[temp["compra_limpa"].str.len() >= 4]

    grupos = temp.groupby(["compra_limpa", "valor_parcela_base"], dropna=False)

    for (compra, valor), grupo in grupos:
        qtd_detectada = len(grupo)

        if qtd_detectada < 2:
            continue

        if qtd_detectada > 36:
            continue

        # evita recorrência comum pequena
        if valor < 80 and qtd_detectada > 3:
            continue

        # Regra conservadora:
        # se aparecer repetido 5 vezes, interpreta como 10x com 5 pagas.
        # se aparecer repetido 4 vezes, interpreta como 8x com 4 pagas.
        # se aparecer repetido 2 ou 3 vezes, interpreta como possível 6x.
        if qtd_detectada >= 5:
            total_estimado = qtd_detectada * 2
        elif qtd_detectada == 4:
            total_estimado = 8
        else:
            total_estimado = 6

        parcela_atual = qtd_detectada
        total_parcelas = max(total_estimado, parcela_atual)

        resultado.append(
            criar_item(
                compra=compra,
                categoria=grupo.iloc[0].get("categoria", "Outros"),
                parcela_atual=parcela_atual,
                total_parcelas=total_parcelas,
                valor_parcela=float(valor),
                descricao=f"Parcelamento provável por repetição: {compra} apareceu {qtd_detectada}x",
                tipo="PROVAVEL_REPETICAO",
            )
        )

    return resultado


def processar_parcelamentos(df):
    if df is None or df.empty:
        return pd.DataFrame()

    temp = df.copy()

    coluna_desc = encontrar_coluna_descricao(temp)
    coluna_valor = encontrar_coluna_valor(temp)

    if coluna_desc is None or coluna_valor is None:
        return pd.DataFrame()

    temp[coluna_valor] = pd.to_numeric(temp[coluna_valor], errors="coerce").fillna(0)

    resultado = []
    resultado.extend(detectar_explicitos(temp, coluna_desc, coluna_valor))
    resultado.extend(detectar_provaveis(temp, coluna_desc, coluna_valor))

    if not resultado:
        return pd.DataFrame()

    df_resultado = pd.DataFrame(resultado)

    df_resultado = df_resultado.drop_duplicates(
        subset=["compra", "valor_parcela", "tipo_detectado"]
    )

    df_resultado = df_resultado.sort_values("valor_restante", ascending=False).reset_index(drop=True)

    return df_resultado


def resumo_parcelamentos(df_parcelamentos):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return {
            "parcelamentos": 0,
            "abertos": 0,
            "quitados": 0,
            "valor_restante": 0.0,
            "valor_total_compras": 0.0,
            "maior_compromisso": 0.0,
        }

    abertos = df_parcelamentos[df_parcelamentos["status"] == "ABERTO"]
    quitados = df_parcelamentos[df_parcelamentos["status"] == "QUITADO"]

    return {
        "parcelamentos": int(len(df_parcelamentos)),
        "abertos": int(len(abertos)),
        "quitados": int(len(quitados)),
        "valor_restante": float(abertos["valor_restante"].sum()) if not abertos.empty else 0.0,
        "valor_total_compras": float(df_parcelamentos["valor_total_compra"].sum()),
        "maior_compromisso": float(abertos["valor_restante"].max()) if not abertos.empty else 0.0,
    }
