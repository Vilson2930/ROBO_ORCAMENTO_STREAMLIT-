# ============================================================
# PDF ENGINE
# ORÇAMENTO INTELIGENTE
# ============================================================

from pathlib import Path
from pypdf import PdfReader

# ============================================================
# LOCALIZAR PDFs
# ============================================================

def localizar_pdfs(pasta_uploads="data/uploads"):

    pasta = Path(pasta_uploads)

    if not pasta.exists():
        return []

    pdfs = sorted(pasta.glob("*.pdf"))

    return pdfs


# ============================================================
# EXTRAIR TEXTO DE UM PDF
# ============================================================

def extrair_texto_pdf(pdf_path, senha=None):

    texto = ""

    try:

        reader = PdfReader(str(pdf_path))

        if reader.is_encrypted:

            if senha:
                reader.decrypt(senha)

        for pagina in reader.pages:

            conteudo = pagina.extract_text()

            if conteudo:
                texto += conteudo + "\n"

    except Exception as erro:

        print(f"Erro ao ler {pdf_path}: {erro}")

    return texto


# ============================================================
# PROCESSAR TODOS OS PDFs
# ============================================================

def processar_pdfs(pasta_uploads="data/uploads", senha=None):

    pdfs = localizar_pdfs(pasta_uploads)

    documentos = []

    for pdf in pdfs:

        texto = extrair_texto_pdf(pdf, senha)

        documentos.append({
            "arquivo": pdf.name,
            "texto": texto
        })

    return documentos


# ============================================================
# RESUMO EXECUTIVO
# ============================================================

def resumo_pdf_engine(pasta_uploads="data/uploads"):

    pdfs = localizar_pdfs(pasta_uploads)

    return {
        "quantidade_pdfs": len(pdfs),
        "arquivos": [pdf.name for pdf in pdfs]
    }
