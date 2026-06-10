# ============================================================
# TRANSACTION ENGINE
# ORÇAMENTO INTELIGENTE
# Versão universal — leitura ampla de faturas brasileiras
#
# Função:
# - Ler compras à vista
# - Ler compras parceladas
# - Ler anuidade
# - Ignorar pagamentos, créditos, totais, limites, boletos, juros e textos institucionais
# - Aceitar formatos Caixa, Nubank, Inter, bancos tradicionais e layouts genéricos
#
# Regra central:
# Toda linha válida precisa ter:
#   DATA + DESCRIÇÃO + VALOR
#
# Exemplos aceitos:
# 29/12 SUPERMERCADO SUPERPAO GUARAPUAVA 37,89D
# 07 MAI •••• 1911 Lobo Motos - Parcela 5/7 R$ 1.039,42
# 23/11 BITGUARD 03 DE 04 OSASCO 457,00D
# 15/03 IFOOD R$ 82,55
# ============================================================

import re
import pandas as pd
import unicodedata


# ============================================================
# MESES
# ============================================================

MESES = {
    "JAN": "01", "JANEIRO": "01",
    "FEV": "02", "FEVEREIRO": "02",
    "MAR": "03", "MARCO": "03", "MARÇO": "03",
    "ABR": "04", "ABRIL": "04",
    "MAI": "05", "MAIO": "05",
    "JUN": "06", "JUNHO": "06",
    "JUL": "07", "JULHO": "07",
    "AGO": "08", "AGOSTO": "08",
    "SET": "09", "SETEMBRO": "09",
    "OUT": "10", "OUTUBRO": "10",
    "NOV": "11", "NOVEMBRO": "11",
    "DEZ": "12", "DEZEMBRO": "12",
}


# ============================================================
# BLOQUEIOS UNIVERSAIS
# ============================================================

BLACKLIST = [
    "FATURA ANTERIOR",
    "PAGAMENTO RECEBIDO",
    "PAGAMENTO EM",
    "OBRIGADO PELO PAGAMENTO",
    "PAGAMENTO TOTAL",
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "PAGAMENTO ON LINE",
    "PAGAMENTO ONLINE",
    "PAGAMENTO PIX",
    "PAGAMENTO BOLETO",
    "PAGAMENTOS E FINANCIAMENTOS",
    "SALDO RESTANTE",
    "SALDO EM ABERTO",
    "SALDO PREVISTO",
    "TOTAL A PAGAR",
    "TOTAL DE COMPRAS",
    "TOTAL COMPRAS",
    "TOTAL FINAL",
    "TOTAL DA FATURA",
    "VALOR TOTAL DA FATURA",
    "VALOR TOTAL DESTA FATURA",
    "VALOR DO DOCUMENTO",
    "VALOR COBRADO",
    "LIMITE TOTAL",
    "LIMITE DISPONIVEL",
    "LIMITE DISPONÍVEL",
    "LIMITES DISPONIVEIS",
    "LIMITES DISPONÍVEIS",
    "VALOR MAXIMO",
    "VALOR MÁXIMO",
    "SAQUE NO CREDITO",
    "SAQUE NO CRÉDITO",
    "PIX NO CREDITO",
    "PIX NO CRÉDITO",
    "BOLETO NO CREDITO",
    "BOLETO NO CRÉDITO",
    "VENCIMENTO",
    "FECHAMENTO",
    "MELHOR DATA",
    "MELHOR DIA",
    "RESUMO DA FATURA",
    "RESUMO",
    "DEMONSTRATIVO",
    "INFORMACOES COMPLEMENTARES",
    "INFORMAÇÕES COMPLEMENTARES",
    "PROGRAMA DE PONTOS",
    "GUIA DE CONSUMO",
    "ENCARGOS",
    "JUROS",
    "IOF",
    "CET",
    "ROTATIVO",
    "MULTA",
    "MORA",
    "ANALISES",
    "ANÁLISES",
    "BANCO CENTRAL",
    "REGISTRATO",
    "SCR",
    "RESOLUCAO",
    "RESOLUÇÃO",
    "DECLARA",
    "LEI 12.007",
    "BOLETO",
    "LINHA DIGITAVEL",
    "LINHA DIGITÁVEL",
    "CODIGO DE BARRAS",
    "CÓDIGO DE BARRAS",
    "AUTENTICACAO MECANICA",
    "AUTENTICAÇÃO MECÂNICA",
    "RECIBO DO PAGADOR",
    "FICHA DE COMPENSACAO",
    "FICHA DE COMPENSAÇÃO",
    "BENEFICIARIO",
    "BENEFICIÁRIO",
    "PAGADOR",
    "SACADOR",
    "AGENCIA",
    "AGÊNCIA",
    "NOSSO NUMERO",
    "NOSSO NÚMERO",
    "CPF",
    "CNPJ",
    "OUVIDORIA",
    "SAC CAIXA",
    "CENTRAL DE ATENDIMENTO",
    "APP CARTOES",
    "APP CARTÕES",
    "BAIXE AGORA",
    "LEGENDA",
    "CHIP E SENHA",
    "POR APROXIMACAO",
    "POR APROXIMAÇÃO",
    "COMPRA PELA INTERNET",
    "TARJA MAGNETICA",
    "TARJA MAGNÉTICA",
    "OPCOES PARA PAGAMENTO",
    "OPÇÕES PARA PAGAMENTO",
    "PARCELAMENTO DE FATURA",
    "PARCELE A SUA FATURA",
    "SIMULAR",
    "SIMULE",
]


CABECALHOS = [
    "DATA DESCRICAO CIDADE PAIS VALOR",
    "DATA DESCRIÇÃO CIDADE PAÍS VALOR",
    "DATA DESCRIÇÃO CIDADE/PAÍS VALOR",
    "DATA DESCRICAO VALOR",
    "DATA DESCRIÇÃO VALOR",
    "TRANSAÇÕES DE",
    "TRANSACOES DE",
    "CRÉDITO/DÉBITO",
    "CREDITO/DEBITO",
    "VALOR U$$",
    "VALOR ORIGINAL",
    "COTAÇÃO",
    "COTACAO",
]


# ============================================================
# PADRÕES
# ============================================================

PADRAO_VALOR = re.compile(
    r"R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\s*[DC]?",
    re.IGNORECASE,
)

PADRAO_VALOR_FINAL = re.compile(
    r"(?P<valor>R?\$?\s*(?:\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}))\s*(?P<dc>[DC])?\s*$",
    re.IGNORECASE,
)

# 29/12 DESCRICAO 37,89D
PADRAO_DATA_NUMERICA = re.compile(
    r"^(?P<data>\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+(?P<resto>.+)$",
    re.IGNORECASE,
)

# 07 MAI DESCRICAO R$ 112,50
PADRAO_DATA_MES_TEXTO = re.compile(
    r"^(?P<dia>\d{1,2})\s+(?P<mes>[A-ZÇ]{3,9})\.?\s+(?P<resto>.+)$",
    re.IGNORECASE,
)

# 11 DE DEZ. 2025 DESCRICAO 84,19
PADRAO_DATA_EXTENSO = re.compile(
    r"^(?P<dia>\d{1,2})\s+DE\s+(?P<mes>[A-ZÇ]{3,12})\.?\s+(?P<ano>\d{4})\s+(?P<resto>.+)$",
    re.IGNORECASE,
)

PADRAO_PARCELA_DE = re.compile(
    r"\b(?:PARCELA\s*)?(?P<atual>\d{1,2})\s*DE\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)

PADRAO_PARCELA_BARRA = re.compile(
    r"\b(?:PARCELA\s*)?(?P<atual>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b",
    re.IGNORECASE,
)

PADRAO_NX = re.compile(
    r"\b(?P<total>\d{1,2})\s*X\b",
    re.IGNORECASE,
)

PADRAO_CARTAO_MASCARADO = re.compile(
    r"[•●*]{2,}\s*\d{4}",
    re.IGNORECASE,
)


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def converter_valor(valor):
    if valor is None:
        return 0.0

    if isinstance(valor, (int, float)):
        try:
            return float(valor)
        except Exception:
            return 0.0

    texto = str(valor).strip()
    texto = texto.replace("R$", "").replace(" ", "")
    texto = re.sub(r"[DCdc]$", "", texto)

    try:
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
            return float(texto)

        return float(texto)

    except Exception:
        return 0.0


def extrair_ano_arquivo(nome_arquivo):
    m = re.search(r"(20\d{2})", str(nome_arquivo))
    return m.group(1) if m else "2026"


def montar_data_numerica(data, arquivo):
    partes = data.split("/")

    if len(partes) == 2:
        dia = partes[0].zfill(2)
        mes = partes[1].zfill(2)
        ano = extrair_ano_arquivo(arquivo)
        return f"{dia}/{mes}/{ano}"

    if len(partes) == 3:
        dia = partes[0].zfill(2)
        mes = partes[1].zfill(2)
        ano = partes[2]

        if len(ano) == 2:
            ano = f"20{ano}"

        return f"{dia}/{mes}/{ano}"

    return None


# ============================================================
# FILTROS
# ============================================================

def linha_cabecalho(linha):
    texto = normalizar_texto(linha)

    return any(normalizar_texto(cab) in texto for cab in CABECALHOS)


def linha_bloqueada(linha):
    texto = normalizar_texto(linha)

    if not texto:
        return True

    if linha_cabecalho(texto):
        return True

    for termo in BLACKLIST:
        if normalizar_texto(termo) in texto:
            return True

    # crédito real/pagamento não entra como gasto
    if texto.endswith("C") and PADRAO_VALOR_FINAL.search(texto):
        return True

    if len(texto) > 220:
        return True

    if texto.count("/") > 8:
        return True

    return False


def descricao_valida(descricao):
    texto = normalizar_texto(descricao)

    if not texto:
        return False

    if len(texto) < 3:
        return False

    if len(texto) > 140:
        return False

    if linha_bloqueada(texto):
        return False

    if not re.search(r"[A-Z]", texto):
        return False

    return True


# ============================================================
# SEÇÕES
# ============================================================

def detectar_secao(linha, estado_atual=None):
    texto = normalizar_texto(linha)

    if "COMPRAS PARCELADAS" in texto or "DESPESAS A VENCER" in texto or "PRÓXIMAS FATURAS" in texto or "PROXIMAS FATURAS" in texto:
        return "PARCELADAS"

    if "TRANSAÇÕES DE" in texto or "TRANSACOES DE" in texto:
        return "TRANSACOES"

    if "COMPRAS (" in texto or texto == "COMPRAS":
        return "COMPRAS"

    if texto == "ANUIDADE" or texto.startswith("ANUIDADE "):
        return "ANUIDADE"

    if (
        "PAGAMENTOS E FINANCIAMENTOS" in texto
        or "TOTAL COMPRAS PARCELADAS" in texto
        or "TOTAL COMPRAS" in texto
        or "TOTAL FINAL" in texto
        or "VALOR TOTAL DESTA FATURA" in texto
        or "LEGENDA" in texto
        or "ENCARGOS" in texto
        or "LIMITES DISPONIVEIS" in texto
        or "LIMITES DISPONÍVEIS" in texto
    ):
        return None

    return estado_atual


# ============================================================
# PARCELAMENTO
# ============================================================

def extrair_parcela(descricao):
    texto = normalizar_texto(descricao)

    m = PADRAO_PARCELA_DE.search(texto)

    if m:
        atual = int(m.group("atual"))
        total = int(m.group("total"))

        if 1 <= atual <= total <= 60:
            return atual, total, "DE"

    m = PADRAO_PARCELA_BARRA.search(texto)

    if m:
        atual = int(m.group("atual"))
        total = int(m.group("total"))

        if 1 <= atual <= total <= 60:
            return atual, total, "BARRA"

    m = PADRAO_NX.search(texto)

    if m:
        total = int(m.group("total"))

        if 1 <= total <= 60:
            return 0, total, "NX"

    return 0, 0, ""


def limpar_descricao(descricao):
    texto = str(descricao or "")

    texto = PADRAO_CARTAO_MASCARADO.sub(" ", texto)
    texto = PADRAO_VALOR.sub(" ", texto)
    texto = re.sub(r"\bPARCELA\s+\d{1,2}\s*/\s*\d{1,2}\b", " ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bPARCELA\s+\d{1,2}\s*DE\s*\d{1,2}\b", " ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b\d{1,2}\s*/\s*\d{1,2}\b", " ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b\d{1,2}\s*DE\s*\d{1,2}\b", " ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b\d{1,2}\s*X\b", " ", texto, flags=re.IGNORECASE)
    texto = texto.replace("R$", " ")
    texto = re.sub(r"[*•●|]+", " ", texto)
    texto = re.sub(r"[-–—]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip(" -")


# ============================================================
# EXTRAÇÃO DE LINHA
# ============================================================

def separar_valor_final(resto):
    m = PADRAO_VALOR_FINAL.search(str(resto or ""))

    if not m:
        return None, None, None

    valor = converter_valor(m.group("valor"))
    dc = str(m.group("dc") or "D").upper()
    descricao = str(resto[:m.start()]).strip()

    return descricao, valor, dc


def montar_item(
    arquivo,
    data,
    descricao,
    valor,
    origem,
    parcelado=False,
    parcela_atual=0,
    total_parcelas=0,
    tipo_parcela="",
    linha_original_pdf="",
):
    descricao_limpa = limpar_descricao(descricao)

    if not descricao_valida(descricao_limpa):
        return None

    valor = converter_valor(valor)

    if valor <= 0:
        return None

    parcela_atual = int(parcela_atual or 0)
    total_parcelas = int(total_parcelas or 0)

    if parcelado:
        if total_parcelas <= 0:
            return None

        if parcela_atual > total_parcelas:
            return None

        valor_parcela = float(valor)
        parcelas_abertas = max(total_parcelas - parcela_atual, 0)
    else:
        parcela_atual = 0
        total_parcelas = 0
        valor_parcela = 0.0
        parcelas_abertas = 0
        tipo_parcela = ""

    return {
        "arquivo_fatura": arquivo,
        "data": data,
        "descricao_original": descricao_limpa,
        "descricao_normalizada": descricao_limpa,
        "valor": float(valor),
        "origem_extracao": origem,
        "parcelado": bool(parcelado),
        "parcela_atual": int(parcela_atual),
        "total_parcelas": int(total_parcelas),
        "parcelas_abertas": int(parcelas_abertas),
        "valor_parcela": float(valor_parcela),
        "tipo_parcela": tipo_parcela,
        "linha_original_pdf": linha_original_pdf or "",
        "confianca_extracao": 95 if origem.startswith("universal") else 85,
    }


def extrair_linha_universal(linha, arquivo, estado=None):
    if linha_bloqueada(linha):
        return None

    linha_original = str(linha)
    linha_norm = normalizar_texto(linha)

    data = None
    resto = None

    m = PADRAO_DATA_NUMERICA.search(linha_original.strip())

    if m:
        data = montar_data_numerica(m.group("data"), arquivo)
        resto = m.group("resto")

    if data is None:
        m = PADRAO_DATA_MES_TEXTO.search(linha_original.strip())

        if m:
            mes_nome = normalizar_texto(m.group("mes"))
            mes = MESES.get(mes_nome)

            if mes:
                dia = m.group("dia").zfill(2)
                ano = extrair_ano_arquivo(arquivo)
                data = f"{dia}/{mes}/{ano}"
                resto = m.group("resto")

    if data is None:
        m = PADRAO_DATA_EXTENSO.search(linha_original.strip())

        if m:
            mes_nome = normalizar_texto(m.group("mes"))
            mes = MESES.get(mes_nome)

            if mes:
                dia = m.group("dia").zfill(2)
                ano = m.group("ano")
                data = f"{dia}/{mes}/{ano}"
                resto = m.group("resto")

    if data is None or not resto:
        return None

    descricao, valor, dc = separar_valor_final(resto)

    if descricao is None or valor is None:
        return None

    if dc == "C":
        return None

    parcela_atual, total_parcelas, tipo_parcela = extrair_parcela(descricao)

    parcelado = total_parcelas > 0

    origem = "universal_parcelado" if parcelado else "universal_avista"

    if estado == "PARCELADAS":
        origem = "universal_secao_parcelada"

    if estado == "COMPRAS":
        origem = "universal_secao_compras"

    if estado == "TRANSACOES":
        origem = "universal_transacoes"

    return montar_item(
        arquivo=arquivo,
        data=data,
        descricao=descricao,
        valor=valor,
        origem=origem,
        parcelado=parcelado,
        parcela_atual=parcela_atual,
        total_parcelas=total_parcelas,
        tipo_parcela=tipo_parcela,
        linha_original_pdf=linha_original,
    )


def extrair_linha_anuidade(linha, arquivo):
    texto = normalizar_texto(linha)

    if not texto.startswith("ANUIDADE"):
        return None

    descricao, valor, dc = separar_valor_final(linha)

    if descricao is None or valor is None:
        return None

    if dc == "C":
        return None

    parcela_atual, total_parcelas, tipo_parcela = extrair_parcela(descricao)
    parcelado = total_parcelas > 0

    return montar_item(
        arquivo=arquivo,
        data=f"01/01/{extrair_ano_arquivo(arquivo)}",
        descricao=descricao,
        valor=valor,
        origem="universal_anuidade",
        parcelado=parcelado,
        parcela_atual=parcela_atual,
        total_parcelas=total_parcelas,
        tipo_parcela=tipo_parcela,
        linha_original_pdf=linha,
    )


# ============================================================
# PROCESSAMENTO
# ============================================================

def extrair_transacoes_texto(texto, arquivo_origem=""):
    transacoes = []
    linhas = [l.strip() for l in str(texto or "").splitlines() if l.strip()]

    estado = None

    for linha in linhas:
        novo_estado = detectar_secao(linha, estado)

        if novo_estado != estado:
            estado = novo_estado
            continue

        if linha_bloqueada(linha):
            continue

        item = None

        if estado == "ANUIDADE":
            item = extrair_linha_anuidade(linha, arquivo_origem)

        if item is None:
            item = extrair_linha_universal(linha, arquivo_origem, estado)

        if item is not None:
            transacoes.append(item)

    return transacoes


def processar_transacoes(documentos):
    todas = []

    for doc in documentos:
        arquivo = doc.get("arquivo", "")
        texto = doc.get("texto", "")

        todas.extend(
            extrair_transacoes_texto(
                texto=texto,
                arquivo_origem=arquivo
            )
        )

    colunas = [
        "arquivo_fatura",
        "data",
        "descricao_original",
        "descricao_normalizada",
        "valor",
        "origem_extracao",
        "parcelado",
        "parcela_atual",
        "total_parcelas",
        "parcelas_abertas",
        "valor_parcela",
        "tipo_parcela",
        "linha_original_pdf",
        "confianca_extracao",
    ]

    df = pd.DataFrame(todas, columns=colunas)

    if df.empty:
        return df

    df["data"] = pd.to_datetime(
        df["data"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    df = df.dropna(subset=["data"])

    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["valor"])
    df = df[df["valor"] > 0]

    df["descricao_original"] = df["descricao_original"].apply(limpar_descricao)
    df["descricao_normalizada"] = df["descricao_original"]

    df = df[df["descricao_original"].apply(descricao_valida)]

    df["parcelado"] = df["parcelado"].fillna(False).astype(bool)
    df["parcela_atual"] = pd.to_numeric(df["parcela_atual"], errors="coerce").fillna(0).astype(int)
    df["total_parcelas"] = pd.to_numeric(df["total_parcelas"], errors="coerce").fillna(0).astype(int)
    df["parcelas_abertas"] = pd.to_numeric(df["parcelas_abertas"], errors="coerce").fillna(0).astype(int)
    df["valor_parcela"] = pd.to_numeric(df["valor_parcela"], errors="coerce").fillna(0)
    df["confianca_extracao"] = pd.to_numeric(df["confianca_extracao"], errors="coerce").fillna(0).astype(int)

    df = df.drop_duplicates(
        subset=[
            "arquivo_fatura",
            "data",
            "descricao_original",
            "valor",
            "parcelado",
            "parcela_atual",
            "total_parcelas",
        ]
    )

    df = df.sort_values(["data", "descricao_original"]).reset_index(drop=True)

    return df


def resumo_transacoes(df_transacoes):
    if df_transacoes is None or df_transacoes.empty:
        return {
            "quantidade": 0,
            "valor_total": 0.0
        }

    return {
        "quantidade": int(len(df_transacoes)),
        "valor_total": float(df_transacoes["valor"].sum())
    }
