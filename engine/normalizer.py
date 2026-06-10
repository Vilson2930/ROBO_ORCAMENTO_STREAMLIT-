# ============================================================
# normalizer.py
# ORÇAMENTO INTELIGENTE
# Normalização nacional de texto, valores e descrições
# Versão corrigida — não transforma 169.95 em 16995
# ============================================================

import re
import unicodedata


# ============================================================
# TEXTO
# ============================================================

def remover_acentos(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def normalizar_texto(texto):
    texto = remover_acentos(texto)
    texto = texto.upper()
    texto = texto.replace("\r", " ")
    texto = texto.replace("\n", " ")
    texto = texto.replace("\t", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


# ============================================================
# VALORES
# ============================================================

def converter_valor(valor):
    """
    Conversor seguro para valores brasileiros.

    Aceita:
    - 169.95        -> 169.95
    - 169,95        -> 169.95
    - R$ 169,95     -> 169.95
    - 1.699,95      -> 1699.95
    - 1699.95       -> 1699.95

    Corrige o bug:
    - 169.95 NÃO vira 16995
    """

    if valor is None:
        return 0.0

    if isinstance(valor, (int, float)):
        try:
            return float(valor)
        except Exception:
            return 0.0

    texto = str(valor).strip()

    if not texto:
        return 0.0

    texto = texto.replace("R$", "")
    texto = texto.replace(" ", "")

    # formato brasileiro: 1.699,95 ou 169,95
    if "," in texto:
        texto = texto.replace(".", "")
        texto = texto.replace(",", ".")

        try:
            return float(texto)
        except Exception:
            return 0.0

    # formato americano / Python: 169.95
    try:
        return float(texto)
    except Exception:
        return 0.0


def formatar_valor(valor):
    try:
        valor = float(valor)
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


# ============================================================
# DESCRIÇÃO
# ============================================================

def limpar_descricao(descricao):
    texto = normalizar_texto(descricao)

    # valores
    texto = re.sub(r"R?\$?\s*[\d\.]+,\d{2}", " ", texto)
    texto = re.sub(r"R?\$?\s*\d+\.\d{2}", " ", texto)

    # datas
    texto = re.sub(r"\b\d{2}/\d{2}(?:/\d{4})?\b", " ", texto)

    # parcelamentos explícitos
    texto = re.sub(r"\bPARCELA\s*\d{1,2}\s*DE\s*\d{1,2}\b", " ", texto)
    texto = re.sub(r"\bPARCELA\s*\d{1,2}\s*/\s*\d{1,2}\b", " ", texto)
    texto = re.sub(r"\bPARC\.?\s*\d{1,2}\s*/\s*\d{1,2}\b", " ", texto)
    texto = re.sub(r"\bPARC\.?\s*\d{1,2}\s*DE\s*\d{1,2}\b", " ", texto)
    texto = re.sub(r"\b\d{1,2}\s*/\s*\d{1,2}\b", " ", texto)
    texto = re.sub(r"\b\d{1,2}\s*DE\s*\d{1,2}\b", " ", texto)
    texto = re.sub(r"\b\d{1,2}\s*X\b", " ", texto)

    # termos de parcelamento
    texto = re.sub(r"COMPRA PARCELADA", " ", texto)
    texto = re.sub(r"PARCELADO SEM JUROS", " ", texto)
    texto = re.sub(r"PARCELADO", " ", texto)
    texto = re.sub(r"PARCELAMENTO", " ", texto)
    texto = re.sub(r"SEM JUROS", " ", texto)
    texto = re.sub(r"\bEM\s*\d{1,2}\s*X\b", " ", texto)
    texto = re.sub(r"\b\d{1,2}\s*PARCELAS\b", " ", texto)
    texto = re.sub(r"\b\d{1,2}\s*PRESTACOES\b", " ", texto)
    texto = re.sub(r"\b\d{1,2}\s*PRESTAÇÕES\b", " ", texto)

    # ruído
    texto = re.sub(r"[*]+", " ", texto)
    texto = re.sub(r"\(\s*\)", " ", texto)
    texto = re.sub(r"[-–—]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip(" -")


# ============================================================
# MERCHANTS
# ============================================================

def normalizar_merchant(texto):
    texto = limpar_descricao(texto)

    substituicoes = {
        "MERC PAGO": "MERCADO PAGO",
        "MERCPAGO": "MERCADO PAGO",
        "MERCADOPAGO": "MERCADO PAGO",
        "MP ": "MERCADO PAGO ",
        "MP*": "MERCADO PAGO ",
        "PAG SEGURO": "PAGSEGURO",
        "PAG*SEGURO": "PAGSEGURO",
        "PAG SEGURO INTERNET": "PAGSEGURO",
        "GET NET": "GETNET",
        "SAFRA PAY": "SAFRAPAY",
        "BLU INSTITUICAO DE PAG": "BLU",
        "BLU INSTITUICAO": "BLU",
        "ADIQPAY": "ADIQ",
        "ADIQPLU": "ADIQ",
        "REDECARD": "REDE",
        "CIELO S A": "CIELO",
        "STONE PAGAMENTOS": "STONE",
        "STONE PAGAMENTO": "STONE",
    }

    for antigo, novo in substituicoes.items():
        texto = texto.replace(antigo, novo)

    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


# ============================================================
# VALIDAÇÃO
# ============================================================

def descricao_valida(descricao, tamanho_min=3, tamanho_max=120):
    texto = normalizar_texto(descricao)

    if not texto:
        return False

    if len(texto) < tamanho_min:
        return False

    if len(texto) > tamanho_max:
        return False

    if not re.search(r"[A-Z]", texto):
        return False

    return True


def gerar_linha_original(linha):
    return str(linha or "").strip()


def preparar_texto_para_busca(texto):
    texto = normalizar_texto(texto)
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()
