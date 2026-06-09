# ============================================================
# PDF ENGINE
# ORÇAMENTO INTELIGENTE
# Versão profissional — Streamlit + auditoria + filtro institucional
# ============================================================

import re
from pypdf import PdfReader


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_texto_pdf(texto):
    if texto is None:
        return ""

    texto = str(texto)

    texto = texto.replace("\r", "\n")
    texto = texto.replace("\t", " ")

    texto = re.sub(r"[ ]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    linhas = []

    for linha in texto.splitlines():
        linha = linha.strip()
        if linha:
            linhas.append(linha)

    return "\n".join(linhas)


def normalizar_linha_para_filtro(linha):
    linha = str(linha or "").upper()

    substituicoes = {
        "Á": "A", "À": "A", "Ã": "A", "Â": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Õ": "O", "Ô": "O",
        "Ú": "U",
        "Ç": "C",
    }

    for original, novo in substituicoes.items():
        linha = linha.replace(original, novo)

    linha = re.sub(r"\s+", " ", linha)

    return linha.strip()


# ============================================================
# FILTRO INSTITUCIONAL
# ============================================================

PADROES_ADMINISTRATIVOS = [
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "ENCARGOS EM CASO DE PAGAMENTO",
    "ENCARGOS ROTATIVOS",
    "ENCARGO ROTATIVO",
    "ROTATIVO",
    "IOF DIARIO",
    "IOF DIÁRIO",
    "IOF ADICIONAL",
    "IOF DO ROTATIVO",
    "JUROS",
    "MULTA",
    "MORA",
    "CET",
    "TAXA EFETIVA",
    "TAXA EFETIVA MENSAL",
    "TAXA EFETIVA ANUAL",
    "VALOR TOTAL FINANCIADO",
    "VALOR FINANCIADO",
    "TOTAL A PAGAR EM ENCARGOS",
    "TOTAL A PAGAR",
    "FINANCIAMENTO",
    "SIMULACAO",
    "SIMULAÇÃO",
    "SIMULADO",
    "PAGAMENTO PARCIAL SIMULADO",
    "SALDO QUE PODE VIRAR ROTATIVO",
    "VALOR FINANCIADO SERA",
    "VALOR FINANCIADO SERÁ",
    "OBSERVACAO SIMULACAO",
    "OBSERVAÇÃO SIMULAÇÃO",
    "CASO DE PAGAMENTO MINIMO",
    "CASO DE PAGAMENTO MÍNIMO",
]


def linha_administrativa(linha):
    linha_norm = normalizar_linha_para_filtro(linha)

    if not linha_norm:
        return True

    for padrao in PADROES_ADMINISTRATIVOS:
        padrao_norm = normalizar_linha_para_filtro(padrao)
        if padrao_norm in linha_norm:
            return True

    return False


def limpar_linhas_administrativas(texto):
    texto = str(texto or "")

    linhas_limpas = []
    removidas = []

    for linha in texto.splitlines():
        linha_original = linha.strip()

        if not linha_original:
            continue

        if linha_original.startswith("--- PAGINA"):
            linhas_limpas.append(linha_original)
            continue

        if linha_administrativa(linha_original):
            removidas.append(linha_original)
            continue

        linhas_limpas.append(linha_original)

    return "\n".join(linhas_limpas), removidas


# ============================================================
# QUALIDADE
# ============================================================

def avaliar_qualidade_texto(texto, paginas):
    texto = str(texto or "")
    tamanho = len(texto.strip())

    if paginas == 0:
        return {
            "qualidade": "erro",
            "alerta": "PDF sem páginas detectáveis.",
            "caracteres": 0
        }

    if tamanho == 0:
        return {
            "qualidade": "vazio",
            "alerta": "Nenhum texto foi extraído. O PDF pode ser imagem ou digitalizado.",
            "caracteres": 0
        }

    caracteres_por_pagina = tamanho / max(paginas, 1)

    if caracteres_por_pagina < 100:
        return {
            "qualidade": "baixa",
            "alerta": "Pouco texto extraído por página. A leitura pode estar incompleta.",
            "caracteres": tamanho
        }

    if caracteres_por_pagina < 400:
        return {
            "qualidade": "media",
            "alerta": "Texto extraído, mas a fatura pode precisar de auditoria.",
            "caracteres": tamanho
        }

    return {
        "qualidade": "alta",
        "alerta": "Texto extraído com boa densidade.",
        "caracteres": tamanho
    }


# ============================================================
# EXTRAÇÃO PDF
# ============================================================

def extrair_texto_pdf(uploaded_file, senha=None):
    nome_arquivo = getattr(uploaded_file, "name", "arquivo_desconhecido")

    try:
        reader = PdfReader(uploaded_file)

        if reader.is_encrypted:
            if not senha:
                return {
                    "arquivo": nome_arquivo,
                    "status": "erro",
                    "erro": "PDF protegido. Senha não informada.",
                    "texto": "",
                    "texto_original": "",
                    "linhas_removidas": [],
                    "paginas": 0,
                    "qualidade": "erro",
                    "alerta": "Informe a senha para desbloquear este PDF.",
                    "caracteres": 0,
                    "linhas_removidas_total": 0
                }

            resultado = reader.decrypt(senha)

            if resultado == 0:
                return {
                    "arquivo": nome_arquivo,
                    "status": "erro",
                    "erro": "Senha incorreta ou PDF não desbloqueado.",
                    "texto": "",
                    "texto_original": "",
                    "linhas_removidas": [],
                    "paginas": 0,
                    "qualidade": "erro",
                    "alerta": "Senha incorreta ou PDF não pôde ser desbloqueado.",
                    "caracteres": 0,
                    "linhas_removidas_total": 0
                }

        textos_paginas = []

        for numero_pagina, pagina in enumerate(reader.pages, start=1):
            try:
                texto_pagina = pagina.extract_text() or ""
            except Exception:
                texto_pagina = ""

            texto_pagina = normalizar_texto_pdf(texto_pagina)

            if texto_pagina:
                textos_paginas.append(
                    f"--- PAGINA {numero_pagina} ---\n{texto_pagina}"
                )

        texto_original = "\n\n".join(textos_paginas)
        texto_original = normalizar_texto_pdf(texto_original)

        texto_filtrado, linhas_removidas = limpar_linhas_administrativas(
            texto_original
        )

        texto_filtrado = normalizar_texto_pdf(texto_filtrado)

        paginas = len(reader.pages)

        avaliacao = avaliar_qualidade_texto(
            texto=texto_filtrado,
            paginas=paginas
        )

        status = "ok"

        if avaliacao["qualidade"] in ["vazio", "baixa"]:
            status = "alerta"

        return {
            "arquivo": nome_arquivo,
            "status": status,
            "erro": "",
            "texto": texto_filtrado,
            "texto_original": texto_original,
            "linhas_removidas": linhas_removidas[:500],
            "linhas_removidas_total": len(linhas_removidas),
            "paginas": paginas,
            "qualidade": avaliacao["qualidade"],
            "alerta": avaliacao["alerta"],
            "caracteres": avaliacao["caracteres"]
        }

    except Exception as erro:
        return {
            "arquivo": nome_arquivo,
            "status": "erro",
            "erro": str(erro),
            "texto": "",
            "texto_original": "",
            "linhas_removidas": [],
            "linhas_removidas_total": 0,
            "paginas": 0,
            "qualidade": "erro",
            "alerta": "Falha ao processar o PDF.",
            "caracteres": 0
        }


# ============================================================
# PROCESSAMENTO EM LOTE
# ============================================================

def processar_pdfs(uploaded_files=None, senha=None):
    documentos = []

    if not uploaded_files:
        return documentos

    for uploaded_file in uploaded_files:
        resultado = extrair_texto_pdf(
            uploaded_file=uploaded_file,
            senha=senha
        )

        documentos.append(resultado)

    return documentos


# ============================================================
# RESUMO
# ============================================================

def resumo_pdfs(documentos):
    if not documentos:
        return {
            "arquivos": 0,
            "ok": 0,
            "alertas": 0,
            "erros": 0,
            "caracteres_total": 0,
            "linhas_removidas_total": 0
        }

    ok = 0
    alertas = 0
    erros = 0
    caracteres_total = 0
    linhas_removidas_total = 0

    for doc in documentos:
        status = doc.get("status", "")

        if status == "ok":
            ok += 1
        elif status == "alerta":
            alertas += 1
        elif status == "erro":
            erros += 1

        caracteres_total += int(doc.get("caracteres", 0) or 0)
        linhas_removidas_total += int(doc.get("linhas_removidas_total", 0) or 0)

    return {
        "arquivos": len(documentos),
        "ok": ok,
        "alertas": alertas,
        "erros": erros,
        "caracteres_total": caracteres_total,
        "linhas_removidas_total": linhas_removidas_total
    }
