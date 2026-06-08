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

CORES = [
    "#22C55E", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6",
    "#06B6D4", "#EC4899", "#84CC16", "#F97316", "#14B8A6"
]

CORES_CATEGORIAS = {
    "Combustível": "#3B82F6",
    "Supermercado": "#22C55E",
    "Alimentação fora de casa": "#F59E0B",
    "Saúde": "#14B8A6",
    "Transporte": "#EAB308",
    "Casa / Utilidades": "#8B5CF6",
    "Vestuário / Compras": "#EC4899",
    "Assinaturas / Digital": "#06B6D4",
    "Educação": "#84CC16",
    "Lazer / Viagens": "#F97316",
    "Serviços / Pagamentos pessoais": "#10B981",
    "Pagamentos / Intermediadores": "#A855F7",
    "Documentação / Impostos": "#64748B",
    "Pets": "#F43F5E",
    "Financeiro / Bancário": "#94A3B8",
    "Outros": "#EF4444"
}

CATEGORIAS_DISPONIVEIS = list(CORES_CATEGORIAS.keys())


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


def escolher_coluna_valor(df):
    numericas = df.select_dtypes(include="number").columns.tolist()

    if not numericas:
        return None

    prioridade = ["valor", "gasto", "total", "soma", "amount", "preco", "preço"]

    for palavra in prioridade:
        for col in numericas:
            nome = str(col).lower()
            if palavra in nome and "percent" not in nome and "%" not in nome and "score" not in nome:
                return col

    return max(numericas, key=lambda c: pd.to_numeric(df[c], errors="coerce").fillna(0).sum())


def preparar_resumo_para_grafico(resumo):
    df = resumo.copy()

    if isinstance(df.index, pd.Index):
        df = df.reset_index()

    categoria_col = None

    for col in df.columns:
        col_lower = str(col).lower()
        if "categoria" in col_lower or col_lower == "index":
            categoria_col = col
            break

    if categoria_col is None:
        categoria_col = df.columns[0]

    valor_col = escolher_coluna_valor(df)

    if valor_col is None:
        return pd.DataFrame(columns=["Categoria", "Valor"])

    df = df[[categoria_col, valor_col]].copy()
    df.columns = ["Categoria", "Valor"]
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    df = df[df["Valor"] > 0]
    df = df.sort_values("Valor", ascending=False)

    return df


def preparar_evolucao_faturas(df):
    base = df.copy()

    coluna_fatura = None

    for col in base.columns:
        nome = str(col).lower()
        if "arquivo" in nome or "fatura" in nome or "pdf" in nome:
            coluna_fatura = col
            break

    valor_col = escolher_coluna_valor(base)

    if valor_col is None:
        return pd.DataFrame(columns=["Fatura", "Valor"])

    if coluna_fatura is None:
        base["Fatura"] = "Fatura analisada"
        coluna_fatura = "Fatura"

    resultado = (
        base.groupby(coluna_fatura)[valor_col]
        .sum()
        .reset_index()
    )

    resultado.columns = ["Fatura", "Valor"]
    resultado["Valor"] = pd.to_numeric(resultado["Valor"], errors="coerce").fillna(0)
    resultado = resultado[resultado["Valor"] > 0]

    resultado = resultado.sort_values("Fatura")

    return resultado


def classificar_score(score):
    try:
        score = float(score)
    except Exception:
        score = 0

    if score >= 80:
        return "🟢 Excelente"
    if score >= 60:
        return "🟡 Atenção"
    return "🔴 Crítico"


def criar_resumo_cliente(gasto_total, df_grafico, parcelas_futuras, score):
    if df_grafico.empty:
        return "Envie suas faturas para gerar um resumo financeiro."

    top3 = df_grafico.head(3).copy()
    total = df_grafico["Valor"].sum()

    linhas = []
    for _, row in top3.iterrows():
        percentual = (row["Valor"] / total) * 100 if total else 0
        linhas.append(f"{row['Categoria']} ({percentual:.1f}%)")

    return (
        f"Você gastou {moeda(gasto_total)} no período analisado. "
        f"As maiores despesas foram {', '.join(linhas)}. "
        f"As parcelas futuras somam {moeda(parcelas_futuras)}. "
        f"Sua saúde financeira está classificada como {classificar_score(score)}. "
        f"A principal prioridade é observar a categoria {df_grafico.iloc[0]['Categoria']}."
    )


def calcular_outros(df_base, gasto_total):
    outros_df = auditar_outros(df_base, top=50)

    valor_outros = 0
    if outros_df is not None and not outros_df.empty:
        try:
            valor_outros = float(outros_df.sum().sum())
        except Exception:
            valor_outros = 0

    percentual_outros = (valor_outros / gasto_total) * 100 if gasto_total else 0
    return valor_outros, percentual_outros


def card_html(titulo, valor, subtitulo="", cor="#22C55E"):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{titulo}</div>
            <div class="kpi-value">{valor}</div>
            <div class="kpi-sub" style="color:{cor};">{subtitulo}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def insight_card(titulo, texto, cor="#2563EB"):
    st.markdown(
        f"""
        <div class="insight-card" style="border-left: 5px solid {cor};">
            <div class="insight-title">{titulo}</div>
            <div class="insight-text">{texto}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.set_page_config(
    page_title="Orçamento Inteligente",
    page_icon="💰",
    layout="wide"
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1380px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020617 0%, #0F172A 100%);
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    .hero-box {
        background: linear-gradient(135deg, #0F172A, #1E293B);
        padding: 28px;
        border-radius: 22px;
        border: 1px solid rgba(255,255,255,0.10);
        margin-bottom: 24px;
    }

    .hero-title {
        font-size: 38px;
        font-weight: 900;
        color: #FFFFFF;
        margin-bottom: 8px;
    }

    .hero-subtitle {
        font-size: 17px;
        color: #CBD5E1;
        line-height: 1.55;
    }

    .section-title {
        font-size: 24px;
        font-weight: 900;
        color: white;
        margin-top: 28px;
        margin-bottom: 14px;
    }

    .kpi-card {
        background: linear-gradient(135deg, #FFFFFF, #F8FAFC);
        padding: 20px;
        border-radius: 18px;
        border: 1px solid #E5E7EB;
        box-shadow: 0px 8px 24px rgba(0,0,0,0.10);
        min-height: 125px;
    }

    .kpi-label {
        font-size: 13px;
        color: #64748B;
        font-weight: 800;
        margin-bottom: 12px;
    }

    .kpi-value {
        font-size: 25px;
        color: #111827;
        font-weight: 900;
        line-height: 1.15;
    }

    .kpi-sub {
        font-size: 13px;
        font-weight: 800;
        margin-top: 10px;
    }

    .insight-card {
        background: #111827;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
        min-height: 140px;
    }

    .insight-title {
        color: #FFFFFF;
        font-size: 18px;
        font-weight: 900;
        margin-bottom: 12px;
    }

    .insight-text {
        color: #CBD5E1;
        font-size: 15px;
        line-height: 1.55;
    }

    .stButton > button {
        border-radius: 12px;
        height: 45px;
        font-weight: 900;
        background: linear-gradient(135deg, #22C55E, #16A34A);
        color: white;
        border: none;
    }

    .status-card {
        background: linear-gradient(135deg, #064E3B, #065F46);
        padding: 14px;
        border-radius: 14px;
        color: #BBF7D0;
        font-weight: 900;
        margin-top: 12px;
    }

    div[role="radiogroup"] label {
        background: transparent;
        padding: 13px 14px;
        border-radius: 13px;
        margin-bottom: 7px;
        cursor: pointer;
        transition: 0.2s;
        border: 1px solid transparent;
    }

    div[role="radiogroup"] label:hover {
        background-color: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.08);
    }

    div[role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(135deg, #22C55E, #2563EB);
        color: white;
        font-weight: 900;
        border: 1px solid rgba(255,255,255,0.18);
    }

    div[role="radiogroup"] label > div:first-child {
        display: none;
    }

    .sidebar-title {
        font-size: 25px;
        font-weight: 900;
        color: white;
        margin-bottom: 4px;
    }

    .sidebar-subtitle {
        font-size: 13px;
        color: #94A3B8;
        margin-bottom: 24px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(
    """
    <div class="sidebar-title">💰 Orçamento</div>
    <div class="sidebar-subtitle">Consultor financeiro automatizado</div>
    """,
    unsafe_allow_html=True
)

pagina = st.sidebar.radio(
    "Menu",
    [
        "🏠 Resumo",
        "📊 Gastos",
        "💳 Parcelas",
        "🧠 Diagnóstico IA",
        "🎯 Plano de Economia",
        "🤖 Ensinar Robô",
        "⚙️ Auditoria"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📄 Faturas")

with st.sidebar.expander("Enviar ou trocar faturas", expanded=True):
    pdfs = st.file_uploader(
        "PDFs da fatura",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

if pdfs:
    st.sidebar.markdown(
        f"""
        <div class="status-card">
        ✅ {len(pdfs)} fatura(s) carregada(s)
        </div>
        """,
        unsafe_allow_html=True
    )

senha_pdf = st.sidebar.text_input("Senha dos PDFs", type="password")
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


st.markdown(
    """
    <div class="hero-box">
        <div class="hero-title">Orçamento Inteligente</div>
        <div class="hero-subtitle">
            Abra suas faturas e veja, em poucos segundos, quanto gastou,
            onde está concentrando dinheiro e qual ação deve tomar primeiro.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


if pagina == "⚙️ Auditoria":

    st.header("Auditoria PDF")

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

df_grafico = preparar_resumo_para_grafico(resumo_categoria)
df_faturas = preparar_evolucao_faturas(df_base)

gasto_total = diagnostico["gasto_total"]
maior_categoria = diagnostico["categoria_principal"]
score = diagnostico["score"]
parcelas_futuras = diagnostico["parcelas_futuras"]
valor_outros, percentual_outros = calcular_outros(df_base, gasto_total)


if pagina == "🏠 Resumo":

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        card_html("Gasto analisado", moeda(gasto_total), "Total das faturas", "#2563EB")
    with c2:
        card_html("Maior concentração", maior_categoria, "Categoria principal", "#F59E0B")
    with c3:
        card_html("Parcelas futuras", moeda(parcelas_futuras), "Compromisso já assumido", "#EF4444")
    with c4:
        card_html("Saúde financeira", classificar_score(score), f"Score {score}/100", "#22C55E")

    st.markdown('<div class="section-title">Resumo do mês</div>', unsafe_allow_html=True)

    resumo_cliente = criar_resumo_cliente(gasto_total, df_grafico, parcelas_futuras, score)
    insight_card("📌 O que aconteceu com seu dinheiro", resumo_cliente, "#22C55E")

    st.markdown('<div class="section-title">Alertas principais</div>', unsafe_allow_html=True)

    a1, a2, a3 = st.columns(3)

    with a1:
        if not df_grafico.empty:
            maior_valor = df_grafico.iloc[0]["Valor"]
            percentual = (maior_valor / df_grafico["Valor"].sum()) * 100
            insight_card(
                "⚠️ Maior atenção",
                f"{df_grafico.iloc[0]['Categoria']} representa {percentual:.1f}% dos seus gastos.",
                "#F59E0B"
            )

    with a2:
        insight_card(
            "🤖 Qualidade da leitura",
            f"A categoria Outros está em {percentual_outros:.1f}%. A meta é manter abaixo de 5%.",
            "#3B82F6"
        )

    with a3:
        insight_card(
            "💳 Parcelamentos",
            f"Você já possui {moeda(parcelas_futuras)} em parcelas futuras.",
            "#EF4444"
        )

    st.markdown('<div class="section-title">Evolução das faturas analisadas</div>', unsafe_allow_html=True)

    if df_faturas.empty:
        st.warning("Não foi possível identificar os valores por fatura.")
    else:
        df_faturas = df_faturas.copy()
        df_faturas["Valor_formatado"] = df_faturas["Valor"].apply(moeda)

        fig_faturas = px.bar(
            df_faturas,
            x="Fatura",
            y="Valor",
            text="Valor_formatado",
            color="Fatura",
            color_discrete_sequence=CORES
        )

        fig_faturas.update_traces(
            texttemplate="%{text}",
            textposition="outside",
            marker_line_width=0
        )

        fig_faturas.update_layout(
            height=360,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=12),
            xaxis_title="",
            yaxis_title="",
            margin=dict(t=25, b=85, l=35, r=35),
            showlegend=False
        )

        fig_faturas.update_xaxes(showgrid=False)
        fig_faturas.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)")

        st.plotly_chart(fig_faturas, use_container_width=True)


elif pagina == "📊 Gastos":

    st.markdown('<div class="section-title">Para onde foi seu dinheiro</div>', unsafe_allow_html=True)

    col_pizza, col_top = st.columns([1, 1])

    with col_pizza:
        fig_pizza = px.pie(
            df_grafico,
            names="Categoria",
            values="Valor",
            hole=0.50,
            color="Categoria",
            color_discrete_map=CORES_CATEGORIAS
        )

        fig_pizza.update_traces(
            textposition="inside",
            textinfo="percent",
            textfont_size=14
        )

        fig_pizza.update_layout(
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=13),
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10)
        )

        st.plotly_chart(fig_pizza, use_container_width=True)

    with col_top:
        top_categorias = df_grafico.head(8).sort_values("Valor", ascending=True).copy()
        top_categorias["Valor_formatado"] = top_categorias["Valor"].apply(moeda)

        fig_cat = px.bar(
            top_categorias,
            x="Valor",
            y="Categoria",
            orientation="h",
            text="Valor_formatado",
            color="Categoria",
            color_discrete_map=CORES_CATEGORIAS
        )

        fig_cat.update_traces(
            texttemplate="%{text}",
            textposition="outside",
            marker_line_width=0
        )

        fig_cat.update_layout(
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=13),
            xaxis_title="",
            yaxis_title="",
            margin=dict(t=10, b=30, l=10, r=110),
            showlegend=False
        )

        fig_cat.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)")
        fig_cat.update_yaxes(showgrid=False)

        st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown('<div class="section-title">Top categorias</div>', unsafe_allow_html=True)

    top5 = df_grafico.head(5)
    cols = st.columns(5)

    for i, (_, row) in enumerate(top5.iterrows()):
        percentual = (row["Valor"] / df_grafico["Valor"].sum()) * 100
        with cols[i]:
            card_html(
                f"{i + 1}º {row['Categoria']}",
                moeda(row["Valor"]),
                f"{percentual:.1f}% do total",
                CORES[i]
            )

    st.markdown('<div class="section-title">Top estabelecimentos</div>', unsafe_allow_html=True)
    merchants_df = top_merchants(df_base, top=10).round(2)
    st.dataframe(merchants_df, use_container_width=True)


elif pagina == "💳 Parcelas":

    st.header("Compras parceladas")

    c1, c2 = st.columns(2)
    with c1:
        card_html("Parcelas futuras", moeda(parcelas_futuras), "Compromisso financeiro", "#EF4444")
    with c2:
        card_html("Faturas analisadas", qtd_pdfs, "Arquivos processados", "#3B82F6")

    st.markdown('<div class="section-title">Detalhamento dos parcelamentos</div>', unsafe_allow_html=True)
    st.dataframe(df_parcelamentos.round(2), use_container_width=True)


elif pagina == "🧠 Diagnóstico IA":

    st.header("Diagnóstico financeiro")

    st.markdown('<div class="section-title">Leitura simples</div>', unsafe_allow_html=True)
    insight_card("🧠 Diagnóstico automático", criar_resumo_cliente(gasto_total, df_grafico, parcelas_futuras, score), "#22C55E")

    st.markdown('<div class="section-title">Relatório técnico</div>', unsafe_allow_html=True)
    st.text(gerar_relatorio_simples(diagnostico))


elif pagina == "🎯 Plano de Economia":

    st.header("Plano de economia")

    st.markdown('<div class="section-title">O que fazer agora</div>', unsafe_allow_html=True)

    if not df_grafico.empty:
        principal = df_grafico.iloc[0]["Categoria"]
        valor_principal = df_grafico.iloc[0]["Valor"]

        insight_card(
            "1. Atacar o maior gasto",
            f"Comece pela categoria {principal}. Ela representa {moeda(valor_principal)} no período analisado.",
            "#F59E0B"
        )

        insight_card(
            "2. Revisar parcelamentos",
            f"Você possui {moeda(parcelas_futuras)} em parcelas futuras. Evite criar novas parcelas antes de reduzir esse compromisso.",
            "#EF4444"
        )

        insight_card(
            "3. Ensinar o robô",
            f"A categoria Outros está em {percentual_outros:.1f}%. Ensine o robô para melhorar a precisão do diagnóstico.",
            "#3B82F6"
        )

    st.markdown('<div class="section-title">Plano gerado pelo sistema</div>', unsafe_allow_html=True)
    st.text(gerar_plano_acao(recomendacoes))


elif pagina == "🤖 Ensinar Robô":

    st.header("Ensinar o robô")

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
