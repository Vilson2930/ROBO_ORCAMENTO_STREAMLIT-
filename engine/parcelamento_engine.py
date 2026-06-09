# ============================================================
# PARCELAMENTO ENGINE
# ORÇAMENTO INTELIGENTE
# Versão correta — lê parcelas pendentes reais: Nx de R$ valor
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


PADRAO_VALOR = re.compile(r"R\$\s*([\d\.]+,\d{2})", re.IGNORECASE)
PADRAO_PARCELA_PENDENTE = re.compile(
    r"(\d{1,2})\s*X\s*DE\s*R\$\s*([\d\.]+,\d{2})",
    re.IGNORECASE
)

TERMOS_BLOQUEADOS = [
    "PAGAMENTO",
    "PIX",
    "BOLETO",
    "ESTORNO",
    "CREDITO",
    "JUROS",
    "IOF",
    "ENCARGOS",
    "ROTATIVO",
    "SALDO",
    "TOTAL DA FATURA",
    "DESPESAS DA FATURA",
    "FATURA",
    "POSTO",
    "SUPERMERCADO",
    "RESTAURANTE",
]


def contem_bloqueado(texto):
    texto = normalizar_texto(texto)
    return any(t in texto for t in TERMOS_BLOQUEADOS)


def limpar_compra(texto):
    texto = normalizar_texto(texto)
    texto = re.sub(r"R\$\s*[\d\.]+,\d{2}", "", texto)
    texto = re.sub(r"\d{1,2}\s*X\s*DE\s*", "", texto)
    texto = re.sub(r"\b\d{2}/\d{2}(?:/\d{4})?\b", "", texto)
    texto = re.sub(r"[*]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" -")


def extrair_parcelas_pendentes_do_texto(texto, arquivo_origem=""):
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]
    resultados = []

    buffer_compra = []
    valor_total = None

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if linha_norm.startswith("--- PAGINA"):
            buffer_compra = []
            valor_total = None
            continue

        m_parcela = PADRAO_PARCELA_PENDENTE.search(linha_norm)

        if m_parcela:
            parcelas_abertas = int(m_parcela.group(1))
            valor_parcela = converter_valor(m_parcela.group(2))

            if valor_parcela <= 0 or parcelas_abertas <= 0:
                continue

            if valor_total is None:
                valores_linha = PADRAO_VALOR.findall(linha_norm)
                if valores_linha:
                    valor_total = converter_valor(valores_linha[0])

            if valor_total is None:
                valor_total = parcelas_abertas * valor_parcela

            compra = " ".join(buffer_compra[-3:])
            compra = limpar_compra(compra)

            if not compra:
                continue

            if contem_bloqueado(compra):
                continue

            resultados.append({
                "arquivo_fatura": arquivo_origem,
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
                "tipo_detectado": "PENDENTE_NX_DE",
                "descricao_detectada": linha,
            })

            buffer_compra = []
            valor_total = None
            continue

        valores = PADRAO_VALOR.findall(linha_norm)

        if valores:
            valor_total = converter_valor(valores[0])
            linha_sem_valor = PADRAO_VALOR.sub("", linha_norm).strip()
            if linha_sem_valor and not contem_bloqueado(linha_sem_valor):
                buffer_compra.append(linha_sem_valor)
            continue

        if len(linha_norm) >= 3 and not contem_bloqueado(linha_norm):
            buffer_compra.append(linha_norm)
            buffer_compra = buffer_compra[-4:]

    return resultados


def processar_parcelamentos(df_or_documentos):
    if df_or_documentos is None:
        return pd.DataFrame()

    registros = []

    if isinstance(df_or_documentos, list):
        for doc in df_or_documentos:
            arquivo = doc.get("arquivo", "")
            texto = doc.get("texto", "")
            registros.extend(
                extrair_parcelas_pendentes_do_texto(
                    texto=texto,
                    arquivo_origem=arquivo
                )
            )

    elif isinstance(df_or_documentos, pd.DataFrame):
        if "texto" in df_or_documentos.columns:
            for _, doc in df_or_documentos.iterrows():
                arquivo = doc.get("arquivo", "")
                texto = doc.get("texto", "")
                registros.extend(
                    extrair_parcelas_pendentes_do_texto(
                        texto=texto,
                        arquivo_origem=arquivo
                    )
                )

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)

    df = df.drop_duplicates(
        subset=["arquivo_fatura", "compra", "valor_parcela", "parcelas_abertas", "valor_restante"]
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
        "valor_total_compras": float(df_parcelamentos["valor_total_compra"].sum()),
        "maior_compromisso": float(abertos["valor_restante"].max()) if not abertos.empty else 0.0,
    }
