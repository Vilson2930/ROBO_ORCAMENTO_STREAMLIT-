# ============================================================
# PDF ENGINE
# ORÇAMENTO INTELIGENTE
# Versão profissional — Streamlit + auditoria + qualidade da extração
# ============================================================

import re
from pypdf import PdfReader


def normalizar_texto_pdf(texto):
    """
    Normaliza o texto extraído sem destruir quebras de linha importantes.
    """

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


def avaliar_qualidade_texto(texto, paginas):
    """
    Avalia se a extração parece boa ou suspeita.
    """

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


def extrair_texto_pdf(uploaded_file, senha=None):
    """
    Lê um PDF enviado pelo Streamlit e retorna texto extraído com auditoria.
    """

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
                    "paginas": 0,
                    "qualidade": "erro",
                    "alerta": "Informe a senha para desbloquear este PDF.",
                    "caracteres": 0
                }

            resultado = reader.decrypt(senha)

            if resultado == 0:
                return {
                    "arquivo": nome_arquivo,
                    "status": "erro",
                    "erro": "Senha incorreta ou PDF não desbloqueado.",
                    "texto": "",
                    "paginas": 0,
                    "qualidade": "erro",
                    "alerta": "Senha incorreta ou PDF não pôde ser desbloqueado.",
                    "caracteres": 0
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

        texto_total = "\n\n".join(textos_paginas)
        texto_total = normalizar_texto_pdf(texto_total)

        paginas = len(reader.pages)

        avaliacao = avaliar_qualidade_texto(
            texto=texto_total,
            paginas=paginas
        )

        status = "ok"

        if avaliacao["qualidade"] in ["vazio", "baixa"]:
            status = "alerta"

        return {
            "arquivo": nome_arquivo,
            "status": status,
            "erro": "",
            "texto": texto_total,
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
            "paginas": 0,
            "qualidade": "erro",
            "alerta": "Falha ao processar o PDF.",
            "caracteres": 0
        }


def processar_pdfs(uploaded_files=None, senha=None):
    """
    Processa múltiplos PDFs enviados pelo Streamlit.
    """

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


def resumo_pdfs(documentos):
    """
    Gera um resumo simples da qualidade dos PDFs processados.
    """

    if not documentos:
        return {
            "arquivos": 0,
            "ok": 0,
            "alertas": 0,
            "erros": 0,
            "caracteres_total": 0
        }

    ok = 0
    alertas = 0
    erros = 0
    caracteres_total = 0

    for doc in documentos:
        status = doc.get("status", "")

        if status == "ok":
            ok += 1
        elif status == "alerta":
            alertas += 1
        elif status == "erro":
            erros += 1

        caracteres_total += int(doc.get("caracteres", 0) or 0)

    return {
        "arquivos": len(documentos),
        "ok": ok,
        "alertas": alertas,
        "erros": erros,
        "caracteres_total": caracteres_total
    }
