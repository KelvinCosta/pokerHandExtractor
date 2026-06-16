import streamlit as st
import polars as pl

def render_cbet_audit(df, hero_cards_df, board_df):
    st.divider()
    st.subheader("🎯 Auditoria de Agressão e Texturas: Continuation Bet (Flop)")

    df_pfr_hero = (
        df.filter(
            (pl.col("player") == "Hero") & 
            (pl.col("street") == "PRE_FLOP") & 
            (pl.col("action_type") == "RAISE")
            )
        .select("hand_id").unique()
    )

    df_flop_action_hero = (
        df.filter(
            (pl.col("player") == "Hero") & 
            (pl.col("street") == "FLOP")
            )
        .select("hand_id").unique()
    )

    df_cbet_oportunidades = df_pfr_hero.join(df_flop_action_hero, on="hand_id", how="inner")
    total_oportunidades = df_cbet_oportunidades.height

    df_cbet_executada = (
        df.filter(
            (pl.col("player") == "Hero") & 
            (pl.col("street") == "FLOP") & 
            (pl.col("action_type") == "BET")
        )
        .join(df_cbet_oportunidades, on="hand_id", how="inner") 
    )
    total_cbets = df_cbet_executada.height

    cbet_pct = ((total_cbets / total_oportunidades) * 100) if total_oportunidades > 0 else 0.0

    col_cb1, col_cb2, col_cb3 = st.columns(3)
    col_cb1.metric("Oportunidades de C-Bet", total_oportunidades)
    col_cb2.metric("C-Bets Executadas", total_cbets)
    col_cb3.metric("Frequência de C-Bet", f"{cbet_pct:.1f}%")

    if total_cbets > 0:
        st.write("🕵️ **O que você está a C-Betar? (Raio-X do Range)**")

        df_pot_flop = (
            df.filter(pl.col("street") == "PRE_FLOP")
            .group_by("hand_id")
            .agg(pl.col("amount").sum().alias("pote_real_flop"))
        )
        
        df_hero_flop_bet = (
            df.filter((pl.col("player") == "Hero") & (pl.col("street") == "FLOP") & (pl.col("action_type") == "BET"))
            .select(["hand_id", "amount"])
        )

        if "flop_suit_type" in df.columns and "flop_pair_type" in df.columns:
            df_texturas = (
                df.select(["hand_id", "flop_suit_type", "flop_pair_type"])
                .drop_nulls(subset=["flop_suit_type", "flop_pair_type"])
                .unique(subset=["hand_id"])
            )
        else:
            df_texturas = pl.DataFrame({"hand_id": [], "flop_suit_type": [], "flop_pair_type": []}, schema={"hand_id": pl.Utf8, "flop_suit_type": pl.Utf8, "flop_pair_type": pl.Utf8})
            st.warning("As colunas 'flop_suit_type' e 'flop_pair_type' não foram encontradas. Reprocesse o Datalake usando o loader.")

        df_cbet_range = (
            df_cbet_executada.select("hand_id")
            .unique()
            .join(hero_cards_df, on="hand_id", how="left")
            .join(board_df, on="hand_id", how="left")
            .join(df_hero_flop_bet, on="hand_id", how="left")
            .join(df_pot_flop, on="hand_id", how="left")
            .join(df_texturas, on="hand_id", how="left")
            .with_columns(
                ((pl.col("amount") / pl.col("pote_real_flop")) * 100).round(1).alias("sizing_flop_pct")
            )
            .select([
                "hand_id", 
                "hero_cards", 
                "board", 
                "flop_suit_type",
                "flop_pair_type",
                pl.col("pote_real_flop").alias("pote_no_flop"), 
                pl.col("amount").alias("hero_bet"), 
                "sizing_flop_pct"
            ]).sort("sizing_flop_pct", descending=True))

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.write("📊 **C-Bets por Textura de Naipe**")
            dist_suit = df_cbet_range.group_by("flop_suit_type").agg(pl.len()).drop_nulls().sort("len", descending=True)
            st.bar_chart(dist_suit.to_pandas(), x="flop_suit_type", y="len")
            
        with col_t2:
            st.write("📊 **C-Bets por Textura de Pares**")
            dist_pair = df_cbet_range.group_by("flop_pair_type").agg(pl.len()).drop_nulls().sort("len", descending=True)
            st.bar_chart(dist_pair.to_pandas(), x="flop_pair_type", y="len")

        st.write("📋 **Lista de Mãos e Texturas**")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            opcoes_naipe = sorted(df_cbet_range["flop_suit_type"].drop_nulls().unique().to_list())
            filtro_naipe = st.multiselect(
                "Filtrar por Naipe:", 
                options=opcoes_naipe, 
                default=opcoes_naipe,
                key="filtro_naipe_cbet"
            )
            
        with col_f2:
            opcoes_par = sorted(df_cbet_range["flop_pair_type"].drop_nulls().unique().to_list())
            filtro_par = st.multiselect(
                "Filtrar por Pares:", 
                options=opcoes_par, 
                default=opcoes_par,
                key="filtro_par_cbet"
            )

        todas_colunas = df_cbet_range.columns
        colunas_selecionadas = st.multiselect(
            "⚙️ Selecione as colunas para visualizar na tabela:",
            options=todas_colunas,
            default=todas_colunas,
            key="colunas_cbet"
        )

        df_cbet_filtrado = df_cbet_range
        if filtro_naipe:
            df_cbet_filtrado = df_cbet_filtrado.filter(pl.col("flop_suit_type").is_in(filtro_naipe))
        if filtro_par:
            df_cbet_filtrado = df_cbet_filtrado.filter(pl.col("flop_pair_type").is_in(filtro_par))

        if colunas_selecionadas:
            st.dataframe(df_cbet_filtrado.select(colunas_selecionadas).to_pandas(), use_container_width=True, hide_index=True)
        else:
            st.warning("Selecione pelo menos uma coluna para visualizar a tabela.")

    else:
        st.info("Nenhuma C-Bet registada no período selecionado.")
