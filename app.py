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


def moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


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

        if col_lower in ["arquivo", "fatura", "pdf", "nome_arquivo"] or "arquivo" in col_lower or "fatura" in col_lower:
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
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .hero-box {
        background: linear-gradient(135deg, #102A43, #243B53);
        padding: 34px;
        border-radius: 20px;
        margin-bottom: 28px;
        border: 1px solid rgba(255,255,255,0.10);
    }

    .hero-title {
        font-size: 48px;
        font-weight: 800;
        color: white;
        margin-bottom: 12px;
    }

    .hero-subtitle {
        font-size: 19px;
        color: #D9E2EC;
        line-height: 1.6;
    }

    .section-title {
        font-size: 28px;
        font-weight: 800;
        color: white;
        margin-top: 28px;
        margin-bottom: 18px;
    }

    div[data-testid="stMetric"] {
        background-color: #161B22;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
    }

    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #FFFFFF;
    }

    div[data-testid="stMetricLabel"] {
        color: #AAB7C4;
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
            Envie suas faturas, descubra para onde seu dinheiro está indo,
            identifique compras parceladas, reduza desperdícios e receba um diagnóstico financeiro claro.
        </div>
    </div>
    """,
    unsafe_allow_html=True
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

analisar = st.sidebar.button("Analisar", use_container_width=True)

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

    st.markdown('<div class="section-title">Resumo financeiro</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Gasto total", moeda(diagnostico["gasto_total"]))
    col2.metric("Parcelas futuras", moeda(diagnostico["parcelas_futuras"]))
    col3.metric("Score financeiro", f"{diagnostico['score']}/100")
    col4.metric("Maior gasto", diagnostico["categoria_principal"])

    st.markdown('<div class="section-title">Distribuição das despesas</div>', unsafe_allow_html=True)

    df_grafico = preparar_resumo_para_grafico(resumo_categoria)

    colgraf1, colgraf2 = st.columns([2, 1])

    with colgraf1:

        fig = px.pie(
            df_grafico,
            names="Categoria",
            values="Valor",
            hole=0.45,
            title="💰 Para onde foi seu dinheiro"
        )

        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            textfont_size=16,
            pull=[0.04 if i == 0 else 0 for i in range(len(df_grafico))]
        )

        fig.update_layout(
            height=750,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                color="white",
                size=16
            ),
            title_font_size=28,
            margin=dict(
                t=80,
                b=20,
                l=20,
                r=20
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    with colgraf2:

        st.subheader("📊 Ranking de gastos")

        ranking = df_grafico.copy()

        ranking["Valor"] = ranking["Valor"].apply(moeda)

        st.dataframe(
            ranking,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")

        maior_categoria = df_grafico.iloc[0]["Categoria"]
        maior_valor = df_grafico.iloc[0]["Valor"]

        percentual = (
            maior_valor /
            df_grafico["Valor"].sum()
        ) * 100

        st.info(
            f"""
            🎯 **Maior gasto**

            **{maior_categoria}**

            Valor: **{moeda(maior_valor)}**

            Participação: **{percentual:.1f}%**
            """
        )

    st.markdown('<div class="section-title">Despesas por fatura</div>', unsafe_allow_html=True)

    df_faturas = preparar_gastos_por_fatura(df_base)

    if df_faturas.empty:
        st.warning("Não foi possível identificar as despesas por fatura.")
    else:
        fig_bar = px.bar(
            df_faturas,
            x="Fatura",
            y="Valor",
            text="Valor",
            title="Gasto total por fatura"
        )

        fig_bar.update_traces(
            texttemplate="R$ %{text:,.2f}",
            textposition="outside"
        )

        fig_bar.update_layout(
            height=520,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=15),
            title_font_size=26,
            xaxis_title="Fatura",
            yaxis_title="Valor gasto",
            margin=dict(t=80, b=80, l=40, r=30)
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown('<div class="section-title">Auditoria dos Outros</div>', unsafe_allow_html=True)

    outros = auditar_outros(df_base, top=50)
    st.dataframe(outros.round(2), use_container_width=True)

    st.markdown('<div class="section-title">Prévia das transações</div>', unsafe_allow_html=True)
    st.dataframe(df_transacoes.head(20), use_container_width=True)


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
