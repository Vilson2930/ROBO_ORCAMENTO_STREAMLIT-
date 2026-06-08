import streamlit as st
import pandas as pd
import plotly.express as px
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
    "Combustível", "Supermercado", "Alimentação fora de casa", "Saúde",
    "Transporte", "Casa / Utilidades", "Vestuário / Compras",
    "Assinaturas / Digital", "Educação", "Lazer / Viagens",
    "Serviços / Pagamentos pessoais", "Pagamentos / Intermediadores",
    "Documentação / Impostos", "Pets", "Financeiro / Bancário", "Outros"
]


def moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


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

    nova = pd.DataFrame([{"merchant": merchant, "categoria": categoria}])
    df = pd.concat([df, nova], ignore_index=True)
    df.to_csv(USER_RULES_PATH, index=False)

    return True


def preparar_resumo_para_grafico(resumo):
    df = resumo.copy()

    if isinstance(df.index, pd.Index):
        df = df.reset_index()

    categoria_col = None
    valor_col = None

    for col in df.columns:
        col_lower = str(col).lower()

        if "categoria" in col_lower or col_lower == "index":
            categoria_col = col

        if "valor" in col_lower or "total" in col_lower or "gasto" in col_lower:
            valor_col = col

    if categoria_col is None:
        categoria_col = df.columns[0]

    if valor_col is None:
        valor_col = df.select_dtypes(include="number").columns[0]

    df = df[[categoria_col, valor_col]].copy()
    df.columns = ["Categoria", "Valor"]
    df = df[df["Valor"] > 0]
    df = df.sort_values("Valor", ascending=False)

    return df


def preparar_gastos_por_fatura(df):
    base = df.copy()

    coluna_fatura = None
    coluna_valor = None

    for col in base.columns:
        col_lower = str(col).lower()

        if "arquivo" in col_lower or "fatura" in col_lower or "pdf" in col_lower:
            coluna_fatura = col

        if "valor" in col_lower or "total" in col_lower or "gasto" in col_lower:
            coluna_valor = col

    if coluna_valor is None:
        numeros = base.select_dtypes(include="number").columns
        if len(numeros) == 0:
            return pd.DataFrame(columns=["Fatura", "Valor"])
        coluna_valor = numeros[0]

    if coluna_fatura is None:
        base["Fatura"] = "Fatura consolidada"
        coluna_fatura = "Fatura"

    resultado = (
        base.groupby(coluna_fatura)[coluna_valor]
        .sum()
        .reset_index()
        .sort_values(coluna_valor, ascending=False)
    )

    resultado.columns = ["Fatura", "Valor"]
    resultado = resultado[resultado["Valor"] > 0]

    return resultado


st.set_page_config(
    page_title="Orçamento Inteligente",
    page_icon="💰",
    layout="wide"
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    .hero-box {
        background: linear-gradient(135deg, #0F172A, #1E293B);
        padding: 30px;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 25px;
    }

    .hero-title {
        font-size: 44px;
        font-weight: 800;
        color: white;
        margin-bottom: 8px;
    }

    .hero-subtitle {
        font-size: 18px;
        color: #CBD5E1;
        line-height: 1.5;
    }

    .section-title {
        font-size: 25px;
        font-weight: 800;
        color: white;
        margin-top: 28px;
        margin-bottom: 15px;
    }

    .side-card {
        background-color: #111827;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 12px;
    }

    div[data-testid="stMetric"] {
        background-color: #111827;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
    }

    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #FFFFFF;
    }

    div[data-testid="stMetricLabel"] {
        color: #94A3B8;
        font-size: 15px;
    }

    section[data-testid="stSidebar"] {
        background-color: #020617;
    }

    .stButton > button {
        border-radius: 12px;
        height: 45px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="hero-box">
        <div class="hero-title">💰 Orçamento Inteligente</div>
        <div class="hero-subtitle">
            Transforme suas faturas em diagnóstico financeiro. Veja onde seu dinheiro está indo,
            identifique excessos, acompanhe parcelamentos e receba um plano de ação simples.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.title("Orçamento Inteligente")

pagina = st.sidebar.radio(
    "Menu",
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

st.sidebar.markdown("### Enviar faturas")

pdfs = st.sidebar.file_uploader(
    "PDFs da fatura",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

if pdfs:
    st.sidebar.success(f"{len(pdfs)} fatura(s) carregada(s)")

senha_pdf = st.sidebar.text_input(
    "Senha dos PDFs",
    type="password"
)

analisar = st.sidebar.button("Analisar faturas", use_container_width=True)

if analisar:

    if not pdfs:
        st.warning("Envie pelo menos uma fatura em PDF.")

    elif not senha_pdf:
        st.warning("Digite a senha dos PDFs.")

    else:
        with st.spinner("Analisando suas faturas..."):

            documentos = processar_pdfs(uploaded_files=pdfs, senha=senha_pdf)

            df_transacoes = processar_transacoes(documentos)
            df_base = processar_merchants(df_transacoes)
            df_base = processar_categorias(df_base)
            resumo_categoria = resumo_categorias(df_base)
            df_parcelamentos = processar_parcelamentos(df_base)
            resumo_parcelas = resumo_parcelamentos(df_parcelamentos)

            diagnostico = gerar_diagnostico(resumo_categoria, df_parcelamentos)

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
            st.session_state["qtd_pdfs"] = len(pdfs)

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
qtd_pdfs = st.session_state.get("qtd_pdfs", 0)


if pagina == "Dashboard":

    df_grafico = preparar_resumo_para_grafico(resumo_categoria)
    df_faturas = preparar_gastos_por_fatura(df_base)

    gasto_total = diagnostico["gasto_total"]
    maior_categoria = diagnostico["categoria_principal"]
    score = diagnostico["score"]
    parcelas_futuras = diagnostico["parcelas_futuras"]

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Gasto total", moeda(gasto_total))
    col2.metric("Faturas analisadas", qtd_pdfs)
    col3.metric("Parcelas futuras", moeda(parcelas_futuras))
    col4.metric("Score financeiro", f"{score}/100")
    col5.metric("Maior gasto", maior_categoria)

    st.markdown('<div class="section-title">Principais despesas por categoria</div>', unsafe_allow_html=True)

    top_categorias = df_grafico.head(10).sort_values("Valor", ascending=True)

    fig_cat = px.bar(
        top_categorias,
        x="Valor",
        y="Categoria",
        orientation="h",
        text="Valor",
        title=None
    )

    fig_cat.update_traces(
        texttemplate="R$ %{text:,.2f}",
        textposition="outside",
        marker_line_width=0
    )

    fig_cat.update_layout(
        height=520,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=15),
        xaxis_title="",
        yaxis_title="",
        margin=dict(t=20, b=40, l=20, r=80),
        showlegend=False
    )

    fig_cat.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)")
    fig_cat.update_yaxes(showgrid=False)

    st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown('<div class="section-title">Resumo executivo</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])

    with c1:
        maior_valor = df_grafico.iloc[0]["Valor"]
        percentual = (maior_valor / df_grafico["Valor"].sum()) * 100

        st.info(
            f"""
            🎯 **Maior concentração de gasto**

            Categoria: **{df_grafico.iloc[0]["Categoria"]}**

            Valor: **{moeda(maior_valor)}**

            Participação no total: **{percentual:.1f}%**
            """
        )

    with c2:
        outros_df = auditar_outros(df_base, top=50)
        valor_outros = 0

        if outros_df is not None and not outros_df.empty:
            try:
                valor_outros = float(outros_df.sum().sum())
            except Exception:
                valor_outros = 0

        st.info(
            f"""
            🤖 **Qualidade da classificação**

            O sistema combinou regras nacionais com aprendizado do usuário.

            Categoria Outros: **{moeda(valor_outros)}**

            Objetivo: manter Outros abaixo de **5%**.
            """
        )

    st.markdown('<div class="section-title">Gasto total por fatura</div>', unsafe_allow_html=True)

    if df_faturas.empty:
        st.warning("Não foi possível identificar as despesas por fatura.")
    else:
        fig_fat = px.bar(
            df_faturas.sort_values("Valor", ascending=False),
            x="Fatura",
            y="Valor",
            text="Valor",
            title=None
        )

        fig_fat.update_traces(
            texttemplate="R$ %{text:,.2f}",
            textposition="outside",
            marker_line_width=0
        )

        fig_fat.update_layout(
            height=430,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=14),
            xaxis_title="",
            yaxis_title="",
            margin=dict(t=20, b=70, l=40, r=30),
            showlegend=False
        )

        fig_fat.update_xaxes(showgrid=False)
        fig_fat.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)")

        st.plotly_chart(fig_fat, use_container_width=True)

    st.markdown('<div class="section-title">Tabela por categoria</div>', unsafe_allow_html=True)

    tabela_categoria = df_grafico.copy()
    tabela_categoria["Valor"] = tabela_categoria["Valor"].apply(moeda)

    st.dataframe(tabela_categoria, use_container_width=True, hide_index=True)


elif pagina == "Gastos":

    st.header("Para onde foi seu dinheiro")

    st.subheader("Categorias")
    st.dataframe(resumo_categoria.round(2), use_container_width=True)

    st.subheader("Top estabelecimentos")
    st.dataframe(top_merchants(df_base, top=30).round(2), use_container_width=True)

    st.subheader("Transações")
    st.dataframe(df_base.head(100), use_container_width=True)


elif pagina == "Parcelamentos":

    st.header("Compras parceladas")
    st.dataframe(df_parcelamentos.round(2), use_container_width=True)


elif pagina == "Diagnóstico":

    st.header("Diagnóstico financeiro")
    st.text(gerar_relatorio_simples(diagnostico))


elif pagina == "Plano de Ação":

    st.header("Plano de ação")
    st.text(gerar_plano_acao(recomendacoes))


elif pagina == "Aprendizado do Robô":

    st.header("Aprendizado do robô")

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

    if st.button("Salvar aprendizado", use_container_width=True):

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
