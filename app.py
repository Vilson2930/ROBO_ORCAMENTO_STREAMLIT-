import streamlit as st

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Orçamento Inteligente",
    page_icon="💰",
    layout="wide"
)

# ============================================================
# HEADER
# ============================================================

st.title("💰 Orçamento Inteligente")

st.markdown(
    """
    Descubra para onde seu dinheiro está indo,
    identifique parcelamentos e receba um diagnóstico financeiro.
    """
)

# ============================================================
# SIDEBAR
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

# ============================================================
# DASHBOARD
# ============================================================

if pagina == "Dashboard":

    st.header("Resumo Financeiro")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Gasto Total",
            "R$ 0,00"
        )

    with col2:
        st.metric(
            "Parcelas Futuras",
            "R$ 0,00"
        )

    with col3:
        st.metric(
            "Score",
            "0"
        )

    with col4:
        st.metric(
            "Maior Gasto",
            "-"
        )

# ============================================================
# UPLOAD
# ============================================================

st.sidebar.markdown("---")

pdfs = st.sidebar.file_uploader(
    "Enviar Faturas",
    type=["pdf"],
    accept_multiple_files=True
)

senha = st.sidebar.text_input(
    "Senha PDF",
    type="password"
)

if st.sidebar.button("Analisar"):

    st.success(
        "Faturas recebidas com sucesso."
    )
