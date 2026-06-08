# ============================================================
# PDF ENGINE
# ORÇAMENTO INTELIGENTE
# Compatível com Streamlit file_uploader
# ============================================================

from pypdf import PdfReader


def extrair_texto_pdf(uploaded_file, senha=None):
    """
    Lê um PDF enviado pelo Streamlit e retorna texto extraído.
    """

    try:
        reader = PdfReader(uploaded_file)

        if reader.is_encrypted:
            if not senha:
                return {
                    "arquivo": uploaded_file.name,
                    "status": "erro",
                    "erro": "PDF protegido. Senha não informada.",
                    "texto": "",
                    "paginas": 0
                }

            resultado = reader.decrypt(senha)

            if resultado == 0:
                return {
                    "arquivo": uploaded_file.name,
                    "status": "erro",
                    "erro": "Senha incorreta ou PDF não desbloqueado.",
                    "texto": "",
                    "paginas": 0
                }

        texto_total = ""

        for pagina in reader.pages:
            texto = pagina.extract_text() or ""
            texto_total += texto + "\n"

        return {
            "arquivo": uploaded_file.name,
            "status": "ok",
            "erro": "",
            "texto": texto_total,
            "paginas": len(reader.pages)
        }

    except Exception as erro:
        return {
            "arquivo": getattr(uploaded_file, "name", "arquivo_desconhecido"),
            "status": "erro",
            "erro": str(erro),
            "texto": "",
            "paginas": 0
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
