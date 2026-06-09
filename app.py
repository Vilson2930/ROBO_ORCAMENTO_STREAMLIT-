 elif not df_grafico.empty:
        principal = df_grafico.iloc[0]["Categoria"]
        valor_principal = df_grafico.iloc[0]["Valor"]
        economia_estimada = valor_principal * 0.10

        insight_card(
            "1. Atacar o maior gasto",
            f"Comece pela categoria {principal}. Ela representa {moeda(valor_principal)} no período analisado. Uma redução de 10% geraria aproximadamente {moeda(economia_estimada)} de economia.",
            "#F59E0B"
        )

    insight_card(
        "2. Revisar parcelamentos",
        f"Valor futuro comprometido: {moeda(resultado_compromissos['valor_restante_total'])}. Impacto mensal estimado: {moeda(resultado_compromissos['impacto_mensal'])}.",
        "#F59E0B"
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
