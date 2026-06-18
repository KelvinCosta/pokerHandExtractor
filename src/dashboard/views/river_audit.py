import streamlit as st
import polars as pl
from src.dashboard.config import carregar_notas_maos, salvar_nota_mao

def render_river_audit(df, hero_cards_df, board_df):
    vencedores_df = (
        df
        .filter(pl.col("action_type") == "COLLECT")
        .group_by("hand_id")
        .agg(pl.col("player").alias("lista_vencedores"))
        .with_columns(
            pl.col("lista_vencedores").list.contains("Hero").fill_null(False).alias("hero_ganhou")
        )
    )

    auditoria_base = (
        df
        .filter(
            (pl.col("hand_id").str.starts_with("RC")) & 
            (pl.col("street") == "RIVER")
        )
        .group_by("hand_id")
        .agg(
            pl.col("current_pot").first().alias("pote_final"),
            pl.col("invested_amount").filter(pl.col("action_type").is_in(["BET", "CALL", "RAISE"])).sum().alias("investimento_total_river"),
            pl.col("invested_amount").filter((pl.col("player") == "Hero") & (pl.col("action_type") == "BET")).sum().alias("hero_bet_amount"),
            pl.col("is_all_in").filter((pl.col("player") == "Hero") & (pl.col("action_type") == "BET")).any().alias("hero_all_in_river"),
            pl.col("player").filter((pl.col("player") != "Hero") & (pl.col("action_type") == "CALL")).count().alias("qtd_calls_recebidos")
        )
        .filter((pl.col("hero_bet_amount") > 0) & (pl.col("qtd_calls_recebidos") > 0))
        .with_columns((pl.col("pote_final") - pl.col("investimento_total_river")).alias("pote_anterior"))
        .with_columns(((pl.col("hero_bet_amount") / pl.col("pote_anterior")) * 100).round(1).alias("sizing_pct"))
    )

    auditoria_final = (
        auditoria_base
        .join(hero_cards_df, on="hand_id", how="left")
        .join(board_df, on="hand_id", how="left")
        .join(vencedores_df, on="hand_id", how="left")
        .with_columns(
            pl.when(pl.col("hero_ganhou") == True).then(pl.lit("✅ GANHOU")).otherwise(pl.lit("❌ PERDEU")).alias("resultado")
        )
        .select([
            "hand_id", "pote_anterior", "hero_bet_amount", "sizing_pct", "hero_all_in_river", "hero_cards", "board", "resultado"
        ])
        .sort("sizing_pct", descending=False)
    )

    auditoria_ev = (
        auditoria_final
        .with_columns(
            (pl.col("pote_anterior") * 0.75).round(2).alias("bet_ideal_75")
        )
        .with_columns(
            (pl.col("bet_ideal_75") - pl.col("hero_bet_amount")).round(2).alias("diferenca_dolares")
        )
        .with_columns(
            
            pl.when(pl.col("hero_all_in_river"))
            .then(pl.lit("⚖️ All-In (Máximo Possível)"))

            .when((pl.col("resultado") == "✅ GANHOU") & (pl.col("diferenca_dolares") > 0))
            .then(pl.lit("💸 Deixou de ganhar"))
            
            .when((pl.col("resultado") == "❌ PERDEU") & (pl.col("diferenca_dolares") > 0))
            .then(pl.lit("🛡️ Sorte (Poupou)"))
            
            .when((pl.col("resultado") == "✅ GANHOU") & (pl.col("diferenca_dolares") < 0))
            .then(pl.lit("🔥 Extração Máxima (Overbet)"))
            
            .when((pl.col("resultado") == "❌ PERDEU") & (pl.col("diferenca_dolares") < 0))
            .then(pl.lit("🩸 Desperdício"))
            
            .otherwise(pl.lit("⚖️ Na Medida"))
            .alias("impacto_no_caixa")
        )
    )

    col_filtros1, col_filtros2 = st.columns(2)
    with col_filtros1:
        opcoes_resultado = sorted(auditoria_ev["resultado"].unique().to_list())
        filtro_resultado = st.multiselect(
            "Filtro: Resultado da Mão", 
            options=opcoes_resultado, 
            default=opcoes_resultado
        )

    with col_filtros2:
        opcoes_impacto = sorted(auditoria_ev["impacto_no_caixa"].unique().to_list())
        filtro_impacto = st.multiselect(
            "Filtro: Impacto no Caixa", 
            options=opcoes_impacto, 
            default=opcoes_impacto
        )

    if filtro_resultado:
        auditoria_ev = auditoria_ev.filter(pl.col("resultado").is_in(filtro_resultado))
    else:
        # Se esvaziar, mostrar tudo para não quebrar a UX
        pass

    if filtro_impacto:
        auditoria_ev = auditoria_ev.filter(pl.col("impacto_no_caixa").is_in(filtro_impacto))
    else:
        pass

    notas_maos = carregar_notas_maos()
    
    df_pd_ev = auditoria_ev.to_pandas()
    df_pd_ev["Avaliação"] = df_pd_ev["hand_id"].apply(lambda x: notas_maos.get(x, {}).get("flag", "❔ Pendente"))
    df_pd_ev["Anotações"] = df_pd_ev["hand_id"].apply(lambda x: notas_maos.get(x, {}).get("nota", ""))

    edited_df_ev = st.data_editor(
        df_pd_ev,
        column_config={
            "hand_id": st.column_config.TextColumn("Hand ID", disabled=True),
            "pote_anterior": st.column_config.NumberColumn("Pote", format="$%.2f", disabled=True),
            "hero_bet_amount": st.column_config.NumberColumn("Aposta", format="$%.2f", disabled=True),
            "sizing_pct": st.column_config.NumberColumn("Sizing %", format="%.1f%%", disabled=True),
            "hero_all_in_river": st.column_config.CheckboxColumn("All In", disabled=True),
            "hero_cards": st.column_config.TextColumn("Cartas", disabled=True),
            "board": st.column_config.TextColumn("Board", disabled=True),
            "resultado": st.column_config.TextColumn("Resultado", disabled=True),
            "bet_ideal_75": st.column_config.NumberColumn("Bet Ideal 75%", format="$%.2f", disabled=True),
            "diferenca_dolares": st.column_config.NumberColumn("Diferença", format="$%.2f", disabled=True),
            "impacto_no_caixa": st.column_config.TextColumn("Impacto", disabled=True),
            "Avaliação": st.column_config.SelectboxColumn(
                "Avaliação",
                options=["❔ Pendente", "✅ Acerto (Cooler)", "❌ Erro (Value Owned)"],
                required=True
            ),
            "Anotações": st.column_config.TextColumn("Anotações")
        },
        hide_index=True,
        use_container_width=True,
        key="editor_river_ev"
    )

    for i, row in edited_df_ev.iterrows():
        h_id = row["hand_id"]
        nova_nota = row["Anotações"]
        nova_flag = row["Avaliação"]
        old_data = notas_maos.get(h_id, {"nota": "", "flag": "❔ Pendente"})
        
        if nova_nota != old_data["nota"] or nova_flag != old_data["flag"]:
            salvar_nota_mao(h_id, nova_nota, nova_flag)
            notas_maos[h_id] = {"nota": nova_nota, "flag": nova_flag} # Update para próxima tabela

    lucro_perdido = auditoria_ev.filter(
        (pl.col("resultado") == "✅ GANHOU") & (pl.col("diferenca_dolares") > 0)
    )["diferenca_dolares"].sum()

    dinheiro_salvo = auditoria_ev.filter(
        (pl.col("resultado") == "❌ PERDEU") & (pl.col("diferenca_dolares") > 0)
    )["diferenca_dolares"].sum()

    balanco_real = lucro_perdido - dinheiro_salvo

    st.divider()
    st.subheader("💰 Resumo do Caixa do Sprint Atual")
    st.caption("Aviso: Pressupõe stacks infinitos e que o vilão daria Call nos 75%.")

    col1, col2, col3 = st.columns(3)
    col1.metric("💸 Lucro Perdido", f"${lucro_perdido:.2f}")
    col2.metric("🛡️ Dinheiro Salvo", f"${dinheiro_salvo:.2f}")
    col3.metric("📉 Balanço de Vazamento", f"${balanco_real:.2f}", delta="- Vazamento", delta_color="inverse")

    st.divider()
    st.subheader("🛡️ Auditoria de Calls (River)")
    st.write("Análise de todas as mãos onde você decidiu dar **CALL** na última carta (River).")

    df_hero_calls_river = (
        df.filter(
            (pl.col("player") == "Hero") & 
            (pl.col("street") == "RIVER") & 
            (pl.col("action_type") == "CALL")
        )
        .select(["hand_id", "amount"])
        .rename({"amount": "valor_do_call"})
    )

    if df_hero_calls_river.height > 0:
        auditoria_calls = (
            df_hero_calls_river
            .join(hero_cards_df, on="hand_id", how="left")
            .join(board_df, on="hand_id", how="left")
            .join(vencedores_df, on="hand_id", how="left")
            .with_columns(
                pl.when(pl.col("hero_ganhou") == True).then(pl.lit("✅ GANHOU (Hero Call)")).otherwise(pl.lit("❌ PERDEU (Crying Call)")).alias("resultado")
            )
            .select(["hand_id", "valor_do_call", "hero_cards", "board", "resultado"])
            .sort("valor_do_call", descending=True)
        )

        st.write("📝 **Avalie seus Calls:** Marque se o Call foi correto ou um erro de avaliação.")
        
        df_pd_calls = auditoria_calls.to_pandas()
        df_pd_calls["Avaliação"] = df_pd_calls["hand_id"].apply(lambda x: notas_maos.get(x, {}).get("flag", "❔ Pendente"))
        df_pd_calls["Anotações"] = df_pd_calls["hand_id"].apply(lambda x: notas_maos.get(x, {}).get("nota", ""))

        edited_df_calls = st.data_editor(
            df_pd_calls,
            column_config={
                "hand_id": st.column_config.TextColumn("Hand ID", disabled=True),
                "valor_do_call": st.column_config.NumberColumn("Valor do Call", format="$%.2f", disabled=True),
                "hero_cards": st.column_config.TextColumn("Cartas", disabled=True),
                "board": st.column_config.TextColumn("Board", disabled=True),
                "resultado": st.column_config.TextColumn("Resultado", disabled=True),
                "Avaliação": st.column_config.SelectboxColumn(
                    "Avaliação",
                    options=["❔ Pendente", "✅ Acerto (Cooler)", "❌ Erro (Value Owned)"],
                    required=True
                ),
                "Anotações": st.column_config.TextColumn("Anotações")
            },
            hide_index=True,
            use_container_width=True,
            key="editor_river_calls"
        )

        for i, row in edited_df_calls.iterrows():
            h_id = row["hand_id"]
            nova_nota = row["Anotações"]
            nova_flag = row["Avaliação"]
            old_data = notas_maos.get(h_id, {"nota": "", "flag": "❔ Pendente"})
            
            if nova_nota != old_data["nota"] or nova_flag != old_data["flag"]:
                salvar_nota_mao(h_id, nova_nota, nova_flag)

        calls_ganhos = auditoria_calls.filter(pl.col("resultado") == "✅ GANHOU (Hero Call)").height
        calls_perdidos = auditoria_calls.filter(pl.col("resultado") == "❌ PERDEU (Crying Call)").height
        winrate_calls = (calls_ganhos / auditoria_calls.height) * 100

        st.caption(f"Você venceu {calls_ganhos} vezes e perdeu {calls_perdidos} vezes ao dar Call no River. (Taxa de acerto: {winrate_calls:.1f}%)")
    else:
        st.info("Nenhum Call no River registrado no período selecionado.")
