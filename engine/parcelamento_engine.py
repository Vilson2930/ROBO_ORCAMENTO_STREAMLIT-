# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão robusta — evita confundir datas, dívida e compras normais
# ============================================================

import re
import pandas as pd


TERMOS_NAO_PARCELAMENTO = [
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "PAGAMENTO PARCIAL",
    "SALDO FINANCIADO",
    "SALDO DEVEDOR",
    "JUROS",
    "JUROS ROTATIVO",
    "IOF",
    "MULTA",
    "ENCARGOS",
    "ENCARGOS FINANCEIROS",
    "BOLETO",
    "PIX",
    "TRANSFERENCIA",
    "TRANSFERÊNCIA",
    "POSTO",
    "SUPERMERCADO",
    "FARMACIA",
    "DROGARIA",
]


def normalizar_texto(texto):
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


def contem_termo_bloqueado(texto):
    texto = normalizar_texto(texto)
    return any(normalizar_texto(t) in texto for t in TERMOS_NAO_PARCELAMENTO)


def extrair_parcela(texto):
    texto = normalizar_texto(texto)

    if contem_termo_bloqueado(texto):
        return None, None

    padroes_fortes = [
        r"\bPARCELA\s*(\d{1,2})\s*DE\s*(\d{1,2})\b",
        r"\bPARC\s*(\d{1,2})\s*DE\s*(\d{1,2})\b",
        r"\bPARC\s*(\d{1,2})\s*/\s*(\d{1,2})\b",
        r"\bCOMPRA\s*PARCELADA\s*(\d{1,2})\s*/\s*(\d{1,2})\b",
        r"\bPARCELADO\s*(\d{1,2})\s*/\s*(\d{1,2})\b",
    ]

    for padrao in padroes_fortes:
        m = re.search(padrao, texto)
        if m:
            atual = int(m.group(1))
            total = int(m.group(2))

            if 1 <= atual <= total and total > 1:
                return atual, total

    # Formato 05/10 ou 03/24:
    # só aceita se estiver perto de palavras de compra parcelada ou merchant conhecido.
    contexto_parcelado = any(p in texto for p in [
        "PARCELA",
        "PARC",
        "PARCELADO",
        "COMPRA PARCELADA",
        "MAGAZINE",
        "MERCADO LIVRE",
        "CASAS BAHIA",
        "KABUM",
        "PONTO FRIO",
        "AMAZON",
        "CVC",
        "DELL",
        "NOTEBOOK",
        "ELETRO",
        "MÓVEIS",
        "MOVEIS"
    ])

    if contexto_parcelado:
        m = re.search(r"\b(\d{1,2})\s*/\s*(\d{1,2})\b", texto)
        if m:
            atual = int(m.group(1))
            total = int(m.group(2))

            if 1 <= atual <= total and total > 1:
                return atual, total

    # Formato 2X, 10X:
    # só aceita se não for termo financeiro/dívida e tiver merchant/comércio na descrição.
    contexto_compra = any(p in texto for p in [
        "MAGAZINE",
        "MERCADO LIVRE",
        "CASAS BAHIA",
        "KABUM",
        "PONTO FRIO",
        "AMAZON",
        "CVC",
        "DELL",
        "LOJA",
        "SHOP",
        "STORE",
        "NOTEBOOK",
        "CELULAR",
        "ELETRO"
    ])

    if contexto_compra:
        m = re.search(r"\b(\d{1,2})\s*X\b", texto)
        if m:
            total = int(m.group(1))

            if total > 1:
                return 1, total

    return None, None


def limpar_compra(texto):
    texto = normalizar_texto(texto)

    padroes_limpeza = [
        r"\bPARCELA\s*\d{1,2}\s*DE\s*\d{1,2}\b",
        r"\bPARC\s*\d{1,2}\s*DE\s*\d{1,2}\b",
        r"\bPARC\s*\d{1,2}\s*/\s*\d{1,2}\b",
        r"\bCOMPRA\s*PARCELADA\s*\d{1,2}\s*/\s*\d{1,2}\b",
        r"\bPARCELADO\s*\d{1,2}\s*/\s*\d{1,2}\b",
        r"\b\d{1,2}\s*/\s*\d{1,2}\b",
        r"\b\d{1,2}\s*X\b",
        r"COMPRA PARCELADA",
        r"PARCELADO",
        r"PARCELAMENTO",
    ]

    for padrao in padroes_limpeza:
        texto = re.sub(padrao, "", texto)

    texto = re.sub(r"\b\d{1,2}\s+DE\s+[A-Z]{3,9}\.?\s+\d{4}\b", "", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip(" -")


def encontrar_coluna_descricao(df):
    candidatos = [
        "descricao_original",
        "descrição_original",
        "descricao",
        "descrição",
        "merchant",
        "estabelecimento",
        "compra",
        "texto",
        "lancamento",
        "lançamento",
    ]

    for candidato in candidatos:
        if candidato in df.columns:
            return candidato

    for col in df.columns:
        if df[col].dtype == "object":
            return col

    return None


def encontrar_coluna_valor(df):
    candidatos = [
        "valor",
        "valor_total",
        "total",
        "amount",
        "gasto",
        "preco",
        "preço",
    ]

    for candidato in candidatos:
        if candidato in df.columns:
            return candidato

    numericas = df.select_dtypes(include="number").columns.tolist()
    return numericas[0] if numericas else None


def processar_parcelamentos(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()

    temp = df.copy()

    coluna_descricao = encontrar_coluna_descricao(temp)
    coluna_valor = encontrar_coluna_valor(temp)

    if coluna_descricao is None or coluna_valor is None:
        return pd.DataFrame()

    temp[coluna_valor] = pd.to_numeric(temp[coluna_valor], errors="coerce").fillna(0)
    temp["descricao_parcelamento"] = temp[coluna_descricao].astype(str)

    temp["parcela_atual"] = temp["descricao_parcelamento"].apply(lambda x: extrair_parcela(x)[0])
    temp["total_parcelas"] = temp["descricao_parcelamento"].apply(lambda x: extrair_parcela(x)[1])
    temp["compra"] = temp["descricao_parcelamento"].apply(limpar_compra)

    parcelados = temp[temp["parcela_atual"].notna()].copy()

    if parcelados.empty:
        return pd.DataFrame()

    resultado = []

    for _, linha in parcelados.iterrows():
        compra = str(linha.get("compra", "")).strip()

        if not compra:
            continue

        if contem_termo_bloqueado(compra):
            continue

        parcela_atual = int(linha["parcela_atual"])
        total_parcelas = int(linha["total_parcelas"])
        valor_parcela = float(linha[coluna_valor])

        parcelas_abertas = max(total_parcelas - parcela_atual, 0)
        valor_total_compra = total_parcelas * valor_parcela
        valor_pago = parcela_atual * valor_parcela
        valor_restante = parcelas_abertas * valor_parcela

        status = "QUITADO" if parcelas_abertas == 0 else "ABERTO"

        resultado.append({
            "compra": compra,
            "categoria": linha.get("categoria", "Outros"),
            "ultima_parcela": parcela_atual,
            "total_parcelas": total_parcelas,
            "parcelas_pagas": parcela_atual,
            "parcelas_abertas": parcelas_abertas,
            "valor_parcela": valor_parcela,
            "valor_total_compra": valor_total_compra,
            "valor_pago": valor_pago,
            "valor_restante": valor_restante,
            "status": status,
            "descricao_detectada": linha.get(coluna_descricao, "")
        })

    if not resultado:
        return pd.DataFrame()

    resultado = pd.DataFrame(resultado)

    resultado = resultado.drop_duplicates(
        subset=["compra", "ultima_parcela", "total_parcelas", "valor_parcela"]
    )

    resultado = resultado.sort_values("valor_restante", ascending=False)

    return resultado


def resumo_parcelamentos(df_parcelamentos):
    if df_parcelamentos is None or len(df_parcelamentos) == 0:
        return {
            "parcelamentos": 0,
            "abertos": 0,
            "quitados": 0,
            "valor_restante": 0,
            "valor_total_compras": 0,
            "maior_compromisso": 0
        }

    abertos = df_parcelamentos[df_parcelamentos["status"] == "ABERTO"]
    quitados = df_parcelamentos[df_parcelamentos["status"] == "QUITADO"]

    return {
        "parcelamentos": len(df_parcelamentos),
        "abertos": len(abertos),
        "quitados": len(quitados),
        "valor_restante": float(df_parcelamentos["valor_restante"].sum()),
        "valor_total_compras": float(df_parcelamentos["valor_total_compra"].sum()),
        "maior_compromisso": float(df_parcelamentos["valor_restante"].max())
    }
