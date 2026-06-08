import streamlit as st
import pandas as pd
from pathlib import Path

from engine.pdf_engine import processar_pdfs
from engine.transaction_engine import processar_transacoes
from engine.merchant_engine import processar_merchants, top_merchants
from engine.category_engine import processar_categorias, resumo_categorias, auditar_outros
from engine.parcelamento_engine import processar_parcelamentos, resumo_parcelamentos
from engine.diagnostico_engine import gerar_diagnostico, gerar_relatorio_simples
from engine.recommendation_engine import gerar_recomendacoes, gerar_plano_acao

USER_RULES_PATH = Path("data/user_rules.csv")

CATEGORIAS_DISPONIVEIS = [
    "Combustível",
    "Supermercado",
    "Alimentação fora de casa",
    "Saúde",
    "Transporte",
    "Casa / Utilidades",
    "Vestuário / Compras",
    "Assinaturas / Digital",
    "Educação",
    "Lazer / Viagens",
    "Serviços / Pagamentos pessoais",
    "Pagamentos / Intermediadores",
    "Documentação / Impostos",
    "Pets",
    "Financeiro / Bancário",
    "Outros"
]


def salvar_regra_usuario(merchant, categoria):
    USER_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)

    if USER_RULES_PATH.exists():
        df = pd.read_csv(USER_RULES_PATH)
    else:
        df = pd.DataFrame(columns=["merchant", "categoria"])

    merchant = str(merchant).strip()
    categoria = str(categoria).strip()

    if not merchant or not categoria:
        return False

    df = df[df["merchant"].str.upper() != merchant.upper()]

    nova = pd.DataFrame([{
        "merchant": merchant,
        "categoria": categoria
    }])

    df = pd.concat([df, nova], ignore_index=True)
    df.to_csv(USER_RULES_PATH, index=False)

    return True


st.set_page_config(
    page_title="Orçamento Inteligente",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Orçamento Inteligente")

st.markdown(
    """
    Envie suas faturas, descubra para onde seu dinheiro está indo,
    veja compras parceladas e receba um diagnóstico simples.
    """
)

st.sidebar.title("Menu")

pagina = st.sidebar.radio(
    "Navegação",
    [
        "Dashboard",
        "Gastos",
        "Parcelamentos",
        "Diagnóstico",
        "Plano de Ação",
        "Aprendizado do Robô",
        "Debug PDF"
    ]
)

st.sidebar.markdown("---")

pdfs = st.sidebar.file_uploader(
    "Enviar faturas em PDF",
    type=["pdf"],
    accept_multiple_files=True
)

senha_pdf = st.sidebar.text_input(
    "Senha dos PDFs",
    type="password"
)

analisar = st.sidebar.button("Analisar")

if analisar:

    if not pdfs:
        st.warning("Envie pelo menos uma fatura em PDF.")

    elif not senha_pdf:
        st.warning("Digite a senha dos PDFs.")

    else:
        with st.spinner("Analisando suas faturas..."):

            documentos = processar_pdfs(
                uploaded_files=pdfs,
                senha=senha_pdf
            )

            df_transacoes = processar_transacoes(documentos)
            df_base = processar_merchants(df_transacoes)
            df_base = processar_categorias(df_base)
            resumo_categoria = resumo_categorias(df_base)
            df_parcelamentos = processar_parcelamentos(df_base)
            resumo_parcelas = resumo_parcelamentos(df_parcelamentos)

            diagnostico = gerar_diagnostico(
                resumo_categoria,
                df_parcelamentos
            )

            recomendacoes = gerar_recomendacoes(
                resumo_categoria,
                diagnostico,
                df_parcelamentos
            )

            st.session_state["documentos"] = documentos
            st.session_state["df_transacoes"] = df_transacoes
            st.session_state["df_base"] = df_base
            st.session_state["resumo_categoria"] = resumo_categoria
            st.session_state["df_parcelamentos"] = df_parcelamentos
            st.session_state["diagnostico"] = diagnostico
            st.session_state["recomendacoes"] = recomendacoes
            st.session_state["resumo_parcelas"] = resumo_parcelas

        st.success("Análise concluída com sucesso.")

if pagina == "Debug PDF":

    st.header("Debug PDF")

    if "documentos" not in st.session_state:
        st.info("Envie as faturas, digite a senha e clique em Analisar.")
        st.stop()

    documentos = st.session_state["documentos"]
    df_transacoes = st.session_state.get("df_transacoes", pd.DataFrame())

    for doc in documentos:
        st.markdown(f"### Arquivo: {doc.get('arquivo', '-')}")
        st.write("Status:", doc.get("status", "-"))
        st.write("Erro:", doc.get("erro", "-"))
        st.write("Páginas:", doc.get("paginas", 0))

        texto = doc.get("texto", "")

        st.write("Quantidade de caracteres extraídos:", len(texto))

        st.text_area(
            f"Texto extraído de {doc.get('arquivo', '-')}",
            texto[:8000],
            height=350
        )

    st.subheader("Transações encontradas")
    st.dataframe(df_transacoes.head(50), use_container_width=True)
    st.stop()


dados_prontos = "diagnostico" in st.session_state

if not dados_prontos:
    st.info("Envie suas faturas e clique em Analisar para gerar o diagnóstico.")
    st.stop()

documentos = st.session_state["documentos"]
df_transacoes = st.session_state["df_transacoes"]
df_base = st.session_state["df_base"]
resumo_categoria = st.session_state["resumo_categoria"]
df_parcelamentos = st.session_state["df_parcelamentos"]
diagnostico = st.session_state["diagnostico"]
recomendacoes = st.session_state["recomendacoes"]


if pagina == "Dashboard":

    st.header("Resumo Financeiro")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Gasto Total", f"R$ {diagnostico['gasto_total']:,.2f}")
    col2.metric("Parcelas Futuras", f"R$ {diagnostico['parcelas_futuras']:,.2f}")
    col3.metric("Score Financeiro", f"{diagnostico['score']}/100")
    col4.metric("Maior Gasto", diagnostico["categoria_principal"])

    st.subheader("Gastos por Categoria")
    st.dataframe(resumo_categoria.round(2), use_container_width=True)

    st.subheader("Auditoria dos Outros")
    outros = auditar_outros(df_base, top=50)
    st.dataframe(outros.round(2), use_container_width=True)

    st.subheader("Prévia das Transações")
    st.dataframe(df_transacoes.head(20), use_container_width=True)


elif pagina == "Gastos":

    st.header("Para Onde Foi Seu Dinheiro")

    st.subheader("Categorias")
    st.dataframe(resumo_categoria.round(2), use_container_width=True)

    st.subheader("Top Estabelecimentos")
    st.dataframe(top_merchants(df_base, top=30).round(2), use_container_width=True)

    st.subheader("Transações")
    st.dataframe(df_base.head(100), use_container_width=True)


elif pagina == "Parcelamentos":

    st.header("Compras Parceladas")
    st.dataframe(df_parcelamentos.round(2), use_container_width=True)


elif pagina == "Diagnóstico":

    st.header("Diagnóstico Financeiro")
    st.text(gerar_relatorio_simples(diagnostico))


elif pagina == "Plano de Ação":

    st.header("Plano de Ação")
    st.text(gerar_plano_acao(recomendacoes))


elif pagina == "Aprendizado do Robô":

    st.header("Aprendizado do Robô")

    st.info(
        "Aqui você ensina o robô a classificar estabelecimentos que caíram em Outros. "
        "Depois de salvar, clique em Analisar novamente."
    )

    outros = auditar_outros(df_base, top=100)

    if outros is None or outros.empty:
        st.success("Não há estabelecimentos relevantes em Outros.")
        st.stop()

    st.subheader("Maiores lançamentos em Outros")
    st.dataframe(outros.round(2), use_container_width=True)

    merchants = list(outros.index)

    merchant_escolhido = st.selectbox(
        "Escolha o estabelecimento para ensinar o robô:",
        merchants
    )

    categoria_escolhida = st.selectbox(
        "Escolha a categoria correta:",
        CATEGORIAS_DISPONIVEIS
    )

    if st.button("Salvar aprendizado"):

        ok = salvar_regra_usuario(
            merchant=merchant_escolhido,
            categoria=categoria_escolhida
        )

        if ok:
            st.success(
                f"Regra salva: {merchant_escolhido} → {categoria_escolhida}. "
                "Agora clique em Analisar novamente para atualizar os resultados."
            )
        else:
            st.error("Não foi possível salvar a regra.")
