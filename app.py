import streamlit as st
import pandas as pd

from engine.pdf_engine import processar_pdfs
from engine.transaction_engine import processar_transacoes
from engine.merchant_engine import processar_merchants, top_merchants
from engine.category_engine import processar_categorias, resumo_categorias
from engine.parcelamento_engine import processar_parcelamentos, resumo_parcelamentos
from engine.diagnostico_engine import gerar_diagnostico, gerar_relatorio_simples
from engine.recommendation_engine import gerar_recomendacoes, gerar_plano_acao

# ============================================================
# CONFIGURAÇÃO
# ============================================================

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

# ============================================================
# MENU
# ============================================================

st.sidebar.title("Menu")

pagina = st.sidebar.radio(
    "Navegação",
    [
        "Dashboard",
        "Gastos",
        "Parcelamentos",
        "Diagnóstico",
        "Plano de Ação"
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

# ============================================================
# PROCESSAMENTO
# ============================================================

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

            st.session_state["df_base"] = df_base
            st.session_state["resumo_categoria"] = resumo_categoria
            st.session_state["df_parcelamentos"] = df_parcelamentos
            st.session_state["diagnostico"] = diagnostico
            st.session_state["recomendacoes"] = recomendacoes
            st.session_state["resumo_parcelas"] = resumo_parcelas

        st.success("Análise concluída com sucesso.")

# ============================================================
# DADOS
# ============================================================

dados_prontos = "diagnostico" in st.session_state

if not dados_prontos:
    st.info("Envie suas faturas e clique em Analisar para gerar o diagnóstico.")
    st.stop()

df_base = st.session_state["df_base"]
resumo_categoria = st.session_state["resumo_categoria"]
df_parcelamentos = st.session_state["df_parcelamentos"]
diagnostico = st.session_state["diagnostico"]
recomendacoes = st.session_state["recomendacoes"]

# ============================================================
# DASHBOARD
# ============================================================

if pagina == "Dashboard":

    st.header("Resumo Financeiro")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Gasto Total", f"R$ {diagnostico['gasto_total']:,.2f}")
    col2.metric("Parcelas Futuras", f"R$ {diagnostico['parcelas_futuras']:,.2f}")
    col3.metric("Score Financeiro", f"{diagnostico['score']}/100")
    col4.metric("Maior Gasto", diagnostico["categoria_principal"])

    st.subheader("Gastos por Categoria")
    st.dataframe(resumo_categoria.round(2), use_container_width=True)

# ============================================================
# GASTOS
# ============================================================

elif pagina == "Gastos":

    st.header("Para Onde Foi Seu Dinheiro")

    st.subheader("Categorias")
    st.dataframe(resumo_categoria.round(2), use_container_width=True)

    st.subheader("Top Estabelecimentos")
    st.dataframe(top_merchants(df_base, top=30).round(2), use_container_width=True)

# ============================================================
# PARCELAMENTOS
# ============================================================

elif pagina == "Parcelamentos":

    st.header("Compras Parceladas")

    st.dataframe(df_parcelamentos.round(2), use_container_width=True)

# ============================================================
# DIAGNÓSTICO
# ============================================================

elif pagina == "Diagnóstico":

    st.header("Diagnóstico Financeiro")

    st.text(gerar_relatorio_simples(diagnostico))

# ============================================================
# PLANO DE AÇÃO
# ============================================================

elif pagina == "Plano de Ação":

    st.header("Plano de Ação")

    st.text(gerar_plano_acao(recomendacoes))
