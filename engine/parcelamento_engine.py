# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão profissional — lê parcelamentos no texto bruto da fatura
# e cruza com transações limpas
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


def converter_valor(valor):
    return float(str(valor).replace(".", "").replace(",", "."))


def moeda_para_float(texto):
    m = re.search(r"R\$\s*([\d\.]+,\d{2})", str(texto), re.IGNORECASE)
    if not m:
        return None
    return converter_valor(m.group(1))


PADRAO_VALOR = re.compile(r"R\$\s*([\d\.]+,\d{2})", re.IGNORECASE)

PADRAO_NX_DE = re.compile(
    r"(?P<qtd>\d{1,2})\s*X\s*DE\s*R\$\s*(?P<valor>[\d\.]+,\d{2})",
    re.IGNORECASE
)

PADRAO_PARC_EXPLICITA = re.compile(
    r"\b(?:PARC|PARCELA|PARCELADO|COMPRA PARCELADA)\.?\s*(?P<atual>\d{1,2})\s*(?:/|DE)\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

TERMOS_BLOQUEADOS = [
    "PAGAMENTO", "PIX", "BOLETO", "ESTORNO", "CREDITO",
    "JUROS", "IOF", "ENCARGOS", "ROTATIVO", "TOTAL DA FATURA",
    "DESPESAS DA FATURA", "FATURA", "LIMITE", "VENCIMENTO"
]


def contem_bloqueado(texto):
    texto = normalizar_texto(texto)
    return any(t in texto for t in TERMOS_BLOQUEADOS)


def limpar_compra(texto):
    texto = normalizar_texto(texto)

    texto = re.sub(r"R\$\s*[\d\.]+,\d{2}", " ", texto)
    texto = re.sub(r"\d{1,2}\s*X\s*DE\s*R?\$?\s*[\d\.]+,\d{2}", " ", texto)
    texto = re.sub(r"\b(?:PARC|PARCELA|PARCELADO|COMPRA PARCELADA)\.?\s*\d{1,2}\s*(?:/|DE)\s*\d{1,2}\b", " ", texto)
    texto = re.sub(r"\b\d{2}/\d{2}(?:/\d{4})?\b", " ", texto)
    texto = re.sub(r"[*]+", " ", texto)
    texto = re.sub(r"\(\s*\)", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip(" -")


def criar_item(
    compra,
    categoria,
    parcelas_abertas,
    valor_parcela,
    valor_restante,
    descricao,
    tipo,
    arquivo_fatura="",
    ultima_parcela=0,
    total_parcelas=0
):
    parcelas_abertas = int(parcelas_abertas)
    valor_parcela = float(valor_parcela)
    valor_restante = float(valor_restante)

    if total_parcelas <= 0:
        total_parcelas = parcelas_abertas

    return {
        "arquivo_fatura": arquivo_fatura,
        "compra": compra,
        "categoria": categoria,
        "ultima_parcela": int(ultima_parcela),
        "total_parcelas": int(total_parcelas),
        "parcelas_pagas": int(ultima_parcela),
        "parcelas_abertas": parcelas_abertas,
        "valor_parcela": valor_parcela,
        "valor_total_compra": valor_restante,
        "valor_pago": 0.0,
        "valor_restante": valor_restante,
        "status": "ABERTO" if parcelas_abertas > 0 else "QUITADO",
        "tipo_detectado": tipo,
        "descricao_detectada": descricao,
    }


def extrair_blocos_nx_de_texto(texto, arquivo_origem=""):
    """
    Lê blocos reais da fatura no padrão:
    LOJA
    CIDADE
    DATA
    R$ TOTAL
    6x de R$ 291,67
    """

    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    resultados = []

    contexto = []

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if linha_norm.startswith("--- PAGINA"):
            contexto = []
            continue

        m = PADRAO_NX_DE.search(linha_norm)

        if m:
            parcelas_abertas = int(m.group("qtd"))
            valor_parcela = converter_valor(m.group("valor"))

            valor_total = moeda_para_float(linha_norm)

            if valor_total is None:
                valor_total = round(parcelas_abertas * valor_parcela, 2)

            compra = " ".join(contexto[-3:])
            compra = limpar_compra(compra)

            if compra and not contem_bloqueado(compra):
                resultados.append(
                    criar_item(
                        compra=compra,
                        categoria="Outros",
                        parcelas_abertas=parcelas_abertas,
                        valor_parcela=valor_parcela,
                        valor_restante=valor_total,
                        descricao=linha,
                        tipo="PENDENTE_NX_DE",
                        arquivo_fatura=arquivo_origem,
                        ultima_parcela=0,
                        total_parcelas=parcelas_abertas
                    )
                )

            contexto = []
            continue

        if PADRAO_VALOR.search(linha_norm):
            sem_valor = PADRAO_VALOR.sub(" ", linha_norm)
            sem_valor = limpar_compra(sem_valor)

            if sem_valor and not contem_bloqueado(sem_valor):
                contexto.append(sem_valor)

            continue

        if len(linha_norm) >= 3 and not contem_bloqueado(linha_norm):
            contexto.append(linha_norm)
            contexto = contexto[-5:]

    return resultados


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


def detectar_parcelas_explicitas_df(df):
    """
    Só lê parcelamento explícito quando existe PARC, PARCELA ou PARCELADO.
    Não aceita 04/08 sozinho, porque isso pode ser data.
    """

    if df is None or df.empty:
        return []

    coluna_desc = encontrar_coluna_descricao(df)
    coluna_valor = encontrar_coluna_valor(df)

    if coluna_desc is None or coluna_valor is None:
        return []

    temp = df.copy()
    temp[coluna_valor] = pd.to_numeric(temp[coluna_valor], errors="coerce").fillna(0)

    registros = []

    for _, linha in temp.iterrows():
        descricao = str(linha.get(coluna_desc, ""))
        valor_parcela = float(linha.get(coluna_valor, 0))

        if valor_parcela <= 0 or contem_bloqueado(descricao):
            continue

        m = PADRAO_PARC_EXPLICITA.search(normalizar_texto(descricao))

        if not m:
            continue

        atual = int(m.group("atual"))
        total = int(m.group("total"))

        if not (1 <= atual <= total <= 60):
            continue

        compra = limpar_compra(descricao)

        if not compra or contem_bloqueado(compra):
            continue

        registros.append({
            "compra": compra,
            "categoria": linha.get("categoria", "Outros"),
            "parcela_atual": atual,
            "total_parcelas": total,
            "valor_parcela": round(valor_parcela, 2),
            "descricao_detectada": descricao,
        })

    if not registros:
        return []

    base = pd.DataFrame(registros)

    resultado = []

    grupos = base.groupby(
        ["compra", "valor_parcela", "total_parcelas"],
        dropna=False
    )

    for (compra, valor_parcela, total_parcelas), grupo in grupos:
        ultima = int(grupo["parcela_atual"].max())
        total = int(total_parcelas)
        abertas = max(total - ultima, 0)
        valor_restante = abertas * float(valor_parcela)

        resultado.append(
            criar_item(
                compra=compra,
                categoria=grupo.iloc[0].get("categoria", "Outros"),
                parcelas_abertas=abertas,
                valor_parcela=float(valor_parcela),
                valor_restante=valor_restante,
                descricao=" | ".join(grupo["descricao_detectada"].astype(str).unique()[:8]),
                tipo="EXPLICITO_CONSOLIDADO",
                arquivo_fatura="",
                ultima_parcela=ultima,
                total_parcelas=total,
            )
        )

    return resultado


def associar_categoria(parcelamentos, df_base):
    if not parcelamentos or df_base is None or df_base.empty:
        return parcelamentos

    coluna_desc = encontrar_coluna_descricao(df_base)

    if coluna_desc is None or "categoria" not in df_base.columns:
        return parcelamentos

    base = df_base.copy()
    base["_desc_norm"] = base[coluna_desc].apply(normalizar_texto)

    for item in parcelamentos:
        compra_norm = normalizar_texto(item.get("compra", ""))

        if not compra_norm:
            continue

        match = base[base["_desc_norm"].str.contains(compra_norm[:10], regex=False, na=False)]

        if not match.empty:
            item["categoria"] = match.iloc[0].get("categoria", item.get("categoria", "Outros"))

    return parcelamentos


def processar_parcelamentos(documentos=None, df_base=None):
    """
    Uso correto no app.py:
    df_parcelamentos = processar_parcelamentos(documentos=documentos, df_base=df_base)
    """

    registros = []

    if isinstance(documentos, list):
        for doc in documentos:
            arquivo = doc.get("arquivo", "")
            texto = doc.get("texto", "")
            registros.extend(
                extrair_blocos_nx_de_texto(
                    texto=texto,
                    arquivo_origem=arquivo
                )
            )

    registros.extend(detectar_parcelas_explicitas_df(df_base))

    registros = associar_categoria(registros, df_base)

    if not registros:
        return pd.DataFrame(
            columns=[
                "arquivo_fatura", "compra", "categoria", "ultima_parcela",
                "total_parcelas", "parcelas_pagas", "parcelas_abertas",
                "valor_parcela", "valor_total_compra", "valor_pago",
                "valor_restante", "status", "tipo_detectado",
                "descricao_detectada"
            ]
        )

    df = pd.DataFrame(registros)

    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0)
    df["valor_restante"] = pd.to_numeric(df["valor_restante"], errors="coerce").fillna(0)
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce").fillna(0).astype(int)

    df = df[df["valor_parcela"] > 0]
    df = df[df["valor_restante"] > 0]
    df = df[df["parcelas_abertas"] > 0]

    df = df.drop_duplicates(
        subset=["arquivo_fatura", "compra", "parcelas_abertas", "valor_parcela", "valor_restante"]
    )

    df = df.sort_values("valor_restante", ascending=False).reset_index(drop=True)

    return df


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

    return {
        "parcelamentos": int(len(df_parcelamentos)),
        "abertos": int(len(abertos)),
        "quitados": 0,
        "valor_restante": float(abertos["valor_restante"].sum()) if not abertos.empty else 0.0,
        "valor_total_compras": float(df_parcelamentos["valor_restante"].sum()),
        "maior_compromisso": float(abertos["valor_restante"].max()) if not abertos.empty else 0.0,
    }
