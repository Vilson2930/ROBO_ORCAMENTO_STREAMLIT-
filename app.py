import streamlit as st

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Orçamento Inteligente",
    page_icon="💰",
    layout="wide"
)

# ============================================================
# CABEÇALHO
# ============================================================

st.title("💰 Orçamento Inteligente")

st.markdown(
    """
    Descubra para onde seu dinheiro está indo, identifique compras parceladas
    e receba um diagnóstico financeiro simples e objetivo.
    """
)

# ============================================================
# MENU LATERAL
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
# AÇÃO DE ANÁLISE
# ============================================================

if analisar:
    if not pdfs:
        st.warning("Envie pelo menos uma fatura em PDF.")
    elif not senha_pdf:
        st.warning("Digite a senha dos PDFs.")
    else:
        st.success("Faturas recebidas com sucesso. Próxima etapa: conectar os motores de análise.")

# ============================================================
# PÁGINAS
# ============================================================

if pagina == "Dashboard":
    st.header("Resumo Financeiro")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Gasto Total", "R$ 0,00")
    col2.metric("Parcelas Futuras", "R$ 0,00")
    col3.metric("Score Financeiro", "0/100")
    col4.metric("Maior Gasto", "-")

elif pagina == "Gastos":
    st.header("Para Onde Foi Seu Dinheiro")
    st.info("Aqui serão exibidos os gastos por categoria e por estabelecimento.")

elif pagina == "Parcelamentos":
    st.header("Compras Parceladas")
    st.info("Aqui serão exibidas as parcelas pagas, parcelas em aberto e valores futuros.")

elif pagina == "Diagnóstico":
    st.header("Diagnóstico Financeiro")
    st.info("Aqui aparecerá a leitura simples da sua situação financeira.")

elif pagina == "Plano de Ação":
    st.header("Plano de Ação")
    st.info("Aqui o robô mostrará sugestões práticas de economia e organização.")
