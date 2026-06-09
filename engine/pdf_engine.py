# ============================================================
# PDF ENGINE
# ORÇAMENTO INTELIGENTE
# Preserva parcelamentos: 7/10, 09/10, 10X, PARC, PARCELA
# ============================================================

import re
from pypdf import PdfReader


PADRAO_PARCELAMENTO = re.compile(
    r"(\b\d{1,2}\s*/\s*\d{1,2}\b|\b\d{1,2}\s*X\b|PARC|PARCELA|PARCELADO)",
    re.IGNORECASE
)


PADROES_ADMINISTRATIVOS = [
    "PAGAMENTO MINIMO",
    "PAGAMENTO MÍNIMO",
    "PAGAMENTO TOTAL",
    "PAGAMENTO PARCIAL",
    "ENCARGOS EM CASO DE PAGAMENTO",
    "ENCARGOS ROTATIVOS",
    "ROTATIVO",
    "IOF DIARIO",
    "IOF DIÁRIO",
    "IOF ADICIONAL",
    "JUROS",
    "MULTA",
    "MORA",
    "CET",
    "TAXA EFETIVA",
    "VALOR TOTAL FINANCIADO",
    "TOTAL A PAGAR EM ENCARGOS",
    "SALDO QUE PODE VIRAR ROTATIVO",
    "SIMULACAO",
    "SIMULAÇÃO",
]


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


def normalizar_linha(linha):
    linha = str(linha or "").upper()

    trocas = {
        "Á": "A", "À": "A", "Ã": "A", "Â": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Õ": "O", "Ô": "O",
        "Ú": "U",
        "Ç": "C",
    }

    for a, b in trocas.items():
        linha = linha.replace(a, b)

    linha = re.sub(r"\s+", " ", linha)
    return linha.strip()


def linha_tem_parcelamento(linha):
    return bool(PADRAO_PARCELAMENTO.search(str(linha or "")))


def linha_administrativa(linha):
    linha_norm = normalizar_linha(linha)

    if not linha_norm:
        return True

    # REGRA CRÍTICA:
    # se a linha tem 7/10, 09/10, 10X, PARC ou PARCELA,
    # ela nunca deve ser removida pelo PDF Engine.
    if linha_tem_parcelamento(linha_norm):
        return False

    for padrao in PADROES_ADMINISTRATIVOS:
        if normalizar_linha(padrao) in linha_norm:
            return True

    return False


def limpar_linhas_administrativas(texto):
    linhas_limpas = []
    removidas = []
    linhas_com_parcelamento = []

    for linha in str(texto or "").splitlines():
        linha_original = linha.strip()

        if not linha_original:
            continue

        if linha_original.startswith("--- PAGINA"):
            linhas_limpas.append(linha_original)
            continue

        if linha_tem_parcelamento(linha_original):
            linhas_com_parcelamento.append(linha_original)
            linhas_limpas.append(linha_original)
            continue

        if linha_administrativa(linha_original):
            removidas.append(linha_original)
            continue

        linhas_limpas.append(linha_original)

    return "\n".join(linhas_limpas), removidas, linhas_com_parcelamento


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
            "alerta": "Nenhum texto foi extraído.",
            "caracteres": 0
        }

    caracteres_por_pagina = tamanho / max(paginas, 1)

    if caracteres_por_pagina < 100:
        return {
            "qualidade": "baixa",
            "alerta": "Pouco texto extraído por página.",
            "caracteres": tamanho
        }

    if caracteres_por_pagina < 400:
        return {
            "qualidade": "media",
            "alerta": "Texto extraído, mas precisa auditoria.",
            "caracteres": tamanho
        }

    return {
        "qualidade": "alta",
        "alerta": "Texto extraído com boa densidade.",
        "caracteres": tamanho
    }


def extrair_texto_pagina(pagina):
    try:
        texto = pagina.extract_text() or ""
    except Exception:
        texto = ""

    return normalizar_texto_pdf(texto)


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
                    "linhas_parcelamento": [],
                    "paginas": 0,
                    "qualidade": "erro",
                    "alerta": "Informe a senha.",
                    "caracteres": 0,
                    "linhas_removidas_total": 0
                }

            resultado = reader.decrypt(senha)

            if resultado == 0:
                return {
                    "arquivo": nome_arquivo,
                    "status": "erro",
                    "erro": "Senha incorreta.",
                    "texto": "",
                    "texto_original": "",
                    "linhas_removidas": [],
                    "linhas_parcelamento": [],
                    "paginas": 0,
                    "qualidade": "erro",
                    "alerta": "Senha incorreta.",
                    "caracteres": 0,
                    "linhas_removidas_total": 0
                }

        textos_paginas = []

        for numero_pagina, pagina in enumerate(reader.pages, start=1):
            texto_pagina = extrair_texto_pagina(pagina)

            if texto_pagina:
                textos_paginas.append(
                    f"--- PAGINA {numero_pagina} ---\n{texto_pagina}"
                )

        texto_original = normalizar_texto_pdf("\n\n".join(textos_paginas))

        texto_filtrado, linhas_removidas, linhas_parcelamento = limpar_linhas_administrativas(
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
            "linhas_parcelamento": linhas_parcelamento[:500],
            "linhas_removidas_total": len(linhas_removidas),
            "linhas_parcelamento_total": len(linhas_parcelamento),
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
            "linhas_parcelamento": [],
            "linhas_removidas_total": 0,
            "linhas_parcelamento_total": 0,
            "paginas": 0,
            "qualidade": "erro",
            "alerta": "Falha ao processar o PDF.",
            "caracteres": 0
        }


def processar_pdfs(uploaded_files=None, senha=None):
    documentos = []

    if not uploaded_files:
        return documentos

    for uploaded_file in uploaded_files:
        documentos.append(
            extrair_texto_pdf(
                uploaded_file=uploaded_file,
                senha=senha
            )
        )

    return documentos


def resumo_pdfs(documentos):
    if not documentos:
        return {
            "arquivos": 0,
            "ok": 0,
            "alertas": 0,
            "erros": 0,
            "caracteres_total": 0,
            "linhas_removidas_total": 0,
            "linhas_parcelamento_total": 0
        }

    return {
        "arquivos": len(documentos),
        "ok": sum(1 for d in documentos if d.get("status") == "ok"),
        "alertas": sum(1 for d in documentos if d.get("status") == "alerta"),
        "erros": sum(1 for d in documentos if d.get("status") == "erro"),
        "caracteres_total": sum(int(d.get("caracteres", 0) or 0) for d in documentos),
        "linhas_removidas_total": sum(int(d.get("linhas_removidas_total", 0) or 0) for d in documentos),
        "linhas_parcelamento_total": sum(int(d.get("linhas_parcelamento_total", 0) or 0) for d in documentos),
    }
