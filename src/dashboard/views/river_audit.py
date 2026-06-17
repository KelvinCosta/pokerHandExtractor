import streamlit as st
import polars as pl

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
            pl.col("amount").filter(pl.col("action_type").is_in(["BET", "CALL", "RAISE"])).sum().alias("investimento_total_river"),
            pl.col("amount").filter((pl.col("player") == "Hero") & (pl.col("action_type") == "BET")).sum().alias("hero_bet_amount"),
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

    st.dataframe(auditoria_ev.to_pandas(), use_container_width=True, hide_index=True)

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
