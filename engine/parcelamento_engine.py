# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Lê parcelamentos reais em faturas brasileiras
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


PADRAO_VALOR = re.compile(r"R?\$?\s*([\d\.]+,\d{2})", re.IGNORECASE)

PADRAO_NX_DE = re.compile(
    r"(?P<qtd>\d{1,2})\s*X\s*(?:DE)?\s*R?\$?\s*(?P<valor>[\d\.]+,\d{2})",
    re.IGNORECASE
)

TERMOS_BLOQUEADOS = [
    "PAGAMENTO", "PIX", "BOLETO", "ESTORNO", "CREDITO",
    "JUROS", "IOF", "ENCARGOS", "ROTATIVO",
    "TOTAL DA FATURA", "DESPESAS DA FATURA", "LIMITE",
    "VENCIMENTO", "PAGAMENTO MINIMO", "PAGAMENTO TOTAL"
]


def contem_bloqueado(texto):
    texto = normalizar_texto(texto)
    return any(t in texto for t in TERMOS_BLOQUEADOS)


def limpar_compra(texto):
    texto = normalizar_texto(texto)
    texto = re.sub(r"R?\$?\s*[\d\.]+,\d{2}", " ", texto)
    texto = re.sub(r"\d{1,2}\s*X\s*(?:DE)?\s*R?\$?\s*[\d\.]+,\d{2}", " ", texto)
    texto = re.sub(r"\b\d{2}/\d{2}(?:/\d{4})?\b", " ", texto)
    texto = re.sub(r"[*]+", " ", texto)
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

    return True


def criar_item(arquivo, compra, parcelas_abertas, valor_parcela, valor_total, descricao):
    return {
        "arquivo_fatura": arquivo,
        "compra": compra,
        "categoria": "Outros",
        "ultima_parcela": 0,
        "total_parcelas": int(parcelas_abertas),
        "parcelas_pagas": 0,
        "parcelas_abertas": int(parcelas_abertas),
        "valor_parcela": float(valor_parcela),
        "valor_total_compra": float(valor_total),
        "valor_pago": 0.0,
        "valor_restante": float(valor_total),
        "status": "ABERTO",
        "tipo_detectado": "PARCELA_PENDENTE_NX",
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

            valores = PADRAO_VALOR.findall(linha_norm)

            valor_total = None

            if valores:
                candidatos = [converter_valor(v) for v in valores]
                maiores = [v for v in candidatos if v > valor_parcela]
                if maiores:
                    valor_total = max(maiores)

            if valor_total is None and ultimo_valor_total:
                valor_total = ultimo_valor_total

            if valor_total is None:
                valor_total = qtd * valor_parcela

            compra = limpar_compra(" ".join(contexto[-4:]))

            if compra_valida(compra):
                resultados.append(
                    criar_item(
                        arquivo=arquivo,
                        compra=compra,
                        parcelas_abertas=qtd,
                        valor_parcela=valor_parcela,
                        valor_total=valor_total,
                        descricao=linha
                    )
                )

            contexto = []
            ultimo_valor_total = None
            continue

        valores_linha = PADRAO_VALOR.findall(linha_norm)

        if valores_linha:
            candidatos = [converter_valor(v) for v in valores_linha]
            ultimo_valor_total = max(candidatos)

            sem_valor = PADRAO_VALOR.sub(" ", linha_norm)
            sem_valor = limpar_compra(sem_valor)

            if compra_valida(sem_valor):
                contexto.append(sem_valor)

            continue

        if compra_valida(linha_norm):
            contexto.append(linha_norm)
            contexto = contexto[-5:]

    return resultados


def associar_categoria(df_parcelamentos, df_base):
    if df_parcelamentos is None or df_parcelamentos.empty:
        return df_parcelamentos

    if df_base is None or df_base.empty:
        return df_parcelamentos

    if "categoria" not in df_base.columns:
        return df_parcelamentos

    coluna_desc = None

    for col in ["descricao_original", "merchant", "descricao", "estabelecimento"]:
        if col in df_base.columns:
            coluna_desc = col
            break

    if coluna_desc is None:
        return df_parcelamentos

    base = df_base.copy()
    base["_busca"] = base[coluna_desc].apply(normalizar_texto)

    for idx, row in df_parcelamentos.iterrows():
        compra = normalizar_texto(row["compra"])
        chave = compra[:12]

        match = base[base["_busca"].str.contains(chave, regex=False, na=False)]

        if not match.empty:
            df_parcelamentos.at[idx, "categoria"] = match.iloc[0]["categoria"]

    return df_parcelamentos


def processar_parcelamentos(documentos=None, df_base=None):
    registros = []

    if isinstance(documentos, list):
        for doc in documentos:
            registros.extend(
                extrair_parcelamentos_documento(
                    texto=doc.get("texto", ""),
                    arquivo=doc.get("arquivo", "")
                )
            )

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

    df = df.drop_duplicates(
        subset=[
            "arquivo_fatura",
            "compra",
            "parcelas_abertas",
            "valor_parcela",
            "valor_restante"
        ]
    )

    df = associar_categoria(df, df_base)

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
        "valor_restante": float(abertos["valor_restante"].sum()),
        "valor_total_compras": float(df_parcelamentos["valor_restante"].sum()),
        "maior_compromisso": float(abertos["valor_restante"].max()) if not abertos.empty else 0.0,
    }
