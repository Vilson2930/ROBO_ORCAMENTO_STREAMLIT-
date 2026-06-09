# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão corrigida — leitura universal de parcelas em faturas brasileiras
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
    try:
        return float(str(valor).replace(".", "").replace(",", "."))
    except Exception:
        return 0.0


PADRAO_VALOR = re.compile(
    r"R?\$?\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
    re.IGNORECASE
)

PADRAO_NX_DE = re.compile(
    r"(?P<qtd>\d{1,2})\s*[Xx]\s*(?:DE|POR)?\s*R?\$?\s*(?P<valor>[\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
    re.IGNORECASE
)

PADRAO_PARC_EXPLICITA = re.compile(
    r"\b(?:PARC|PARCELA|PARCELADO|COMPRA PARCELADA)\.?\s*(?P<atual>\d{1,2})\s*(?:/|DE)\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE
)

TERMOS_BLOQUEADOS = [
    "PAGAMENTO", "PIX", "BOLETO", "ESTORNO", "CREDITO", "CRÉDITO",
    "JUROS", "IOF", "ENCARGOS", "ROTATIVO", "TOTAL DA FATURA",
    "DESPESAS DA FATURA", "LIMITE", "VENCIMENTO", "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO", "PAGAMENTO TOTAL", "SALDO", "CET"
]


def contem_bloqueado(texto):
    texto = normalizar_texto(texto)
    return any(normalizar_texto(t) in texto for t in TERMOS_BLOQUEADOS)


def limpar_compra(texto):
    texto = normalizar_texto(texto)

    texto = PADRAO_NX_DE.sub(" ", texto)
    texto = PADRAO_PARC_EXPLICITA.sub(" ", texto)
    texto = PADRAO_VALOR.sub(" ", texto)
    texto = re.sub(r"\b\d{2}/\d{2}(?:/\d{4})?\b", " ", texto)
    texto = re.sub(r"[*]+", " ", texto)
    texto = re.sub(r"\(\s*\)", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip(" -")


def compra_valida(compra):
    compra = normalizar_texto(compra)

    if not compra:
        return False

    if len(compra) < 3:
        return False

    if contem_bloqueado(compra):
        return False

    if not re.search(r"[A-Z]", compra):
        return False

    return True


def criar_item(
    arquivo,
    compra,
    parcelas_abertas,
    valor_parcela,
    valor_total,
    descricao,
    tipo="PARCELA_PENDENTE_NX",
    categoria="Outros",
    ultima_parcela=0,
    total_parcelas=None
):
    parcelas_abertas = int(parcelas_abertas)
    valor_parcela = float(valor_parcela)
    valor_total = float(valor_total)

    if total_parcelas is None:
        total_parcelas = parcelas_abertas

    return {
        "arquivo_fatura": arquivo,
        "compra": compra,
        "categoria": categoria,
        "ultima_parcela": int(ultima_parcela),
        "total_parcelas": int(total_parcelas),
        "parcelas_pagas": int(ultima_parcela),
        "parcelas_abertas": int(parcelas_abertas),
        "valor_parcela": float(valor_parcela),
        "valor_total_compra": float(valor_total),
        "valor_pago": 0.0,
        "valor_restante": float(valor_total),
        "status": "ABERTO" if parcelas_abertas > 0 else "QUITADO",
        "tipo_detectado": tipo,
        "descricao_detectada": descricao,
    }


def extrair_parcelamentos_documento(texto, arquivo=""):
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    resultados = []

    contexto = []
    ultimo_valor_total = None

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if linha_norm.startswith("--- PAGINA"):
            contexto = []
            ultimo_valor_total = None
            continue

        m_parcela = PADRAO_NX_DE.search(linha_norm)

        if m_parcela:
            qtd = int(m_parcela.group("qtd"))
            valor_parcela = converter_valor(m_parcela.group("valor"))

            valores = [converter_valor(v) for v in PADRAO_VALOR.findall(linha_norm)]
            candidatos_total = [v for v in valores if v > valor_parcela]

            if candidatos_total:
                valor_total = max(candidatos_total)
            elif ultimo_valor_total and ultimo_valor_total > valor_parcela:
                valor_total = ultimo_valor_total
            else:
                valor_total = qtd * valor_parcela

            compra_mesma_linha = limpar_compra(linha_norm)
            compra_contexto = limpar_compra(" ".join(contexto[-5:]))

            compra = compra_mesma_linha if compra_valida(compra_mesma_linha) else compra_contexto

            if compra_valida(compra):
                resultados.append(
                    criar_item(
                        arquivo=arquivo,
                        compra=compra,
                        parcelas_abertas=qtd,
                        valor_parcela=valor_parcela,
                        valor_total=valor_total,
                        descricao=linha,
                        tipo="PARCELA_PENDENTE_NX"
                    )
                )

            contexto = []
            ultimo_valor_total = None
            continue

        valores_linha = PADRAO_VALOR.findall(linha_norm)

        if valores_linha:
            candidatos = [converter_valor(v) for v in valores_linha]
            ultimo_valor_total = max(candidatos)

            sem_valor = limpar_compra(PADRAO_VALOR.sub(" ", linha_norm))

            if compra_valida(sem_valor):
                contexto.append(sem_valor)
                contexto = contexto[-5:]

            continue

        if compra_valida(linha_norm):
            contexto.append(linha_norm)
            contexto = contexto[-5:]

    return resultados


def encontrar_coluna_descricao(df):
    for col in ["descricao_original", "merchant", "descricao", "estabelecimento", "compra", "texto", "lancamento"]:
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


def extrair_parcelamentos_df(df_base):
    if df_base is None or df_base.empty:
        return []

    coluna_desc = encontrar_coluna_descricao(df_base)
    coluna_valor = encontrar_coluna_valor(df_base)

    if coluna_desc is None or coluna_valor is None:
        return []

    temp = df_base.copy()
    temp[coluna_valor] = pd.to_numeric(temp[coluna_valor], errors="coerce").fillna(0)

    registros = []

    for _, linha in temp.iterrows():
        descricao = str(linha.get(coluna_desc, ""))
        descricao_norm = normalizar_texto(descricao)
        valor = float(linha.get(coluna_valor, 0))
        categoria = linha.get("categoria", "Outros")
        arquivo = linha.get("arquivo_fatura", "")

        if valor <= 0:
            continue

        if contem_bloqueado(descricao_norm):
            continue

        m_nx = PADRAO_NX_DE.search(descricao_norm)

        if m_nx:
            qtd = int(m_nx.group("qtd"))
            valor_parcela = converter_valor(m_nx.group("valor"))
            valor_total = valor if valor > valor_parcela else qtd * valor_parcela
            compra = limpar_compra(descricao_norm)

            if compra_valida(compra):
                registros.append(
                    criar_item(
                        arquivo=arquivo,
                        compra=compra,
                        parcelas_abertas=qtd,
                        valor_parcela=valor_parcela,
                        valor_total=valor_total,
                        descricao=descricao,
                        tipo="DF_NX_DE",
                        categoria=categoria
                    )
                )

            continue

        m_exp = PADRAO_PARC_EXPLICITA.search(descricao_norm)

        if m_exp:
            atual = int(m_exp.group("atual"))
            total = int(m_exp.group("total"))

            if 1 <= atual <= total <= 60:
                abertas = max(total - atual, 0)
                compra = limpar_compra(descricao_norm)
                valor_parcela = valor
                valor_restante = abertas * valor_parcela

                if abertas > 0 and compra_valida(compra):
                    registros.append(
                        criar_item(
                            arquivo=arquivo,
                            compra=compra,
                            parcelas_abertas=abertas,
                            valor_parcela=valor_parcela,
                            valor_total=valor_restante,
                            descricao=descricao,
                            tipo="DF_PARC_EXPLICITA",
                            categoria=categoria,
                            ultima_parcela=atual,
                            total_parcelas=total
                        )
                    )

    return registros


def consolidar_parcelamentos(df):
    if df is None or df.empty:
        return df

    df = df.copy()

    df["compra_norm"] = df["compra"].apply(normalizar_texto)
    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0).round(2)
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce").fillna(0).astype(int)
    df["valor_restante"] = pd.to_numeric(df["valor_restante"], errors="coerce").fillna(0)

    consolidados = []

    grupos = df.groupby(["compra_norm", "valor_parcela"], dropna=False)

    for _, grupo in grupos:
        grupo = grupo.copy()

        # Quando várias faturas antigas foram carregadas, o correto é manter
        # o menor saldo futuro detectado para a mesma compra e mesma parcela.
        escolhido = grupo.sort_values(
            ["parcelas_abertas", "valor_restante"],
            ascending=[True, True]
        ).iloc[0].copy()

        escolhido["descricao_detectada"] = " | ".join(
            grupo["descricao_detectada"].astype(str).unique()[:5]
        )

        consolidados.append(escolhido)

    resultado = pd.DataFrame(consolidados)

    if "compra_norm" in resultado.columns:
        resultado = resultado.drop(columns=["compra_norm"])

    resultado = resultado[resultado["valor_parcela"] > 0]
    resultado = resultado[resultado["valor_restante"] > 0]
    resultado = resultado[resultado["parcelas_abertas"] > 0]

    resultado = resultado.sort_values("valor_restante", ascending=False).reset_index(drop=True)

    return resultado


def associar_categoria(df_parcelamentos, df_base):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return df_parcelamentos

    if df_base is None or df_base.empty:
        return df_parcelamentos

    if "categoria" not in df_base.columns:
        return df_parcelamentos

    coluna_desc = encontrar_coluna_descricao(df_base)

    if coluna_desc is None:
        return df_parcelamentos

    base = df_base.copy()
    base["_busca"] = base[coluna_desc].apply(normalizar_texto)

    for idx, row in df_parcelamentos.iterrows():
        compra = normalizar_texto(row.get("compra", ""))
        chave = compra[:10]

        if not chave:
            continue

        match = base[base["_busca"].str.contains(chave, regex=False, na=False)]

        if not match.empty:
            df_parcelamentos.at[idx, "categoria"] = match.iloc[0].get("categoria", "Outros")

    return df_parcelamentos


def processar_parcelamentos(documentos=None, df_base=None):
    # Compatibilidade com chamada antiga: processar_parcelamentos(df_base)
    if isinstance(documentos, pd.DataFrame) and df_base is None:
        df_base = documentos
        documentos = None

    registros = []

    if isinstance(documentos, list):
        for doc in documentos:
            registros.extend(
                extrair_parcelamentos_documento(
                    texto=doc.get("texto", ""),
                    arquivo=doc.get("arquivo", "")
                )
            )

    registros.extend(extrair_parcelamentos_df(df_base))

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

    df = associar_categoria(df, df_base)
    df = consolidar_parcelamentos(df)

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
        "quitados": int(len(df_parcelamentos) - len(abertos)),
        "valor_restante": float(abertos["valor_restante"].sum()) if not abertos.empty else 0.0,
        "valor_total_compras": float(df_parcelamentos["valor_restante"].sum()),
        "maior_compromisso": float(abertos["valor_restante"].max()) if not abertos.empty else 0.0,
    }
