import streamlit as st
import polars as pl

def render_big_pots(df, df_hero_cards, df_board, df_villains_cards):
    st.title("🔥 Auditoria de Potes Grandes")
    st.write("Dissecação do Lucro (Linhas Azul e Vermelha) exclusivamente em potes inflados (≥ 40 BBs).")

    # 1. Identificar Potes Grandes
    df_pot_sizes = (
        df.group_by("hand_id")
        .agg(
            pl.col("total_pot_final").first().alias("pot_size_usd"),
            pl.col("amount").filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "POST")).max().fill_null(0.02).alias("bb_size"),
            pl.col("date").first().alias("timestamp") # Pega a data da mão
        )
        .with_columns(
            (pl.col("pot_size_usd") / pl.col("bb_size")).alias("pot_in_bb")
        )
        .filter(pl.col("pot_in_bb") >= 40.0)
    )

    if df_pot_sizes.height == 0:
        st.warning("Nenhum pote gigante (≥ 40 BBs) encontrado no período selecionado.")
        return

    # Extrai lista de IDs das mãos gigantes
    maos_gigantes = df_pot_sizes.select("hand_id")

    # 2. Identificar Investimento e Retorno do Hero nessas mãos
    df_hero_investido = (
        df.join(maos_gigantes, on="hand_id", how="inner")
        .filter(
            (pl.col("player") == "Hero") & 
            (~pl.col("action_type").is_in(["COLLECT", "FOLD", "CHECK"]))
        )
        .group_by("hand_id")
        .agg(pl.col("invested_amount").sum().fill_null(0.0).alias("hero_colocou"))
    )

    df_hero_ganhou = (
        df.join(maos_gigantes, on="hand_id", how="inner")
        .filter((pl.col("player") == "Hero") & (pl.col("action_type") == "COLLECT"))
        .group_by("hand_id")
        .agg(pl.col("amount").sum().fill_null(0.0).alias("hero_puxou"))
    )

    # Identificar Mãos com Showdown (mais de um player mostrou cartas)
    showdown_hands = (
        df.join(maos_gigantes, on="hand_id", how="inner")
        .select(["hand_id", "player_cards"]).unique()
        .filter(pl.col("player_cards").list.len() > 1)
        .select("hand_id")
        .with_columns(pl.lit(True).alias("went_to_showdown"))
    )

    # 3. Consolidação PNL
    df_pnl = (
        maos_gigantes
        .join(df_pot_sizes.select(["hand_id", "timestamp", "pot_in_bb"]), on="hand_id", how="left")
        .join(df_hero_investido, on="hand_id", how="left")
        .join(df_hero_ganhou, on="hand_id", how="left")
        .join(showdown_hands, on="hand_id", how="left")
        .fill_null(strategy="zero")
        .with_columns(
            (pl.col("hero_puxou") - pl.col("hero_colocou")).alias("net_profit"),
            pl.col("went_to_showdown").cast(pl.Boolean).fill_null(False)
        )
    )

    # Filtra apenas potes onde Hero estava envolvido (colocou > 0 ou puxou > 0)
    # df_pnl = df_pnl.filter((pl.col("hero_colocou") > 0) | (pl.col("hero_puxou") > 0))

    # Precisamos do game_type
    df_game_types = df.select(["hand_id", "game_type"]).unique()
    df_pnl = df_pnl.join(df_game_types, on="hand_id", how="left")

    tournament_types = ["Tournament", "Spin & Gold", "Mystery Battle Royale"]
    
    # Cash Game
    df_cash_pnl = df_pnl.filter(~pl.col("game_type").is_in(tournament_types))
    sd_winnings_cash = df_cash_pnl.filter(pl.col("went_to_showdown") == True)["net_profit"].sum()
    nsd_winnings_cash = df_cash_pnl.filter(pl.col("went_to_showdown") == False)["net_profit"].sum()
    total_winnings_cash = sd_winnings_cash + nsd_winnings_cash

    # Torneios
    df_tourn_pnl = df_pnl.filter(pl.col("game_type").is_in(tournament_types))
    sd_winnings_tourn = df_tourn_pnl.filter(pl.col("went_to_showdown") == True)["net_profit"].sum()
    nsd_winnings_tourn = df_tourn_pnl.filter(pl.col("went_to_showdown") == False)["net_profit"].sum()
    total_winnings_tourn = sd_winnings_tourn + nsd_winnings_tourn

    # ==========================
    # MÉTRICAS E GRÁFICO
    # ==========================
    st.subheader("💳 Resumo Financeiro (Apenas Potes ≥ 40 BBs)")
    
    if df_cash_pnl.height > 0:
        st.write("#### 💰 Cash Game ($)")
        col1, col2, col3 = st.columns(3)
        col1.metric("💵 Total Net Profit", f"${total_winnings_cash:.2f}")
        col2.info(f"**🔵 Linha Azul (SD Winnings)**\n\n### ${sd_winnings_cash:.2f}")
        col3.error(f"**🔴 Linha Vermelha (Non-SD Winnings)**\n\n### ${nsd_winnings_cash:.2f}")

    if df_tourn_pnl.height > 0:
        st.write("#### 🏆 Torneios (Net Chips)")
        col1_t, col2_t, col3_t = st.columns(3)
        col1_t.metric("💵 Total Net Chips", f"{total_winnings_tourn:,.0f} Chips")
        col2_t.info(f"**🔵 Linha Azul (SD Winnings)**\n\n### {sd_winnings_tourn:,.0f} Chips")
        col3_t.error(f"**🔴 Linha Vermelha (Non-SD Winnings)**\n\n### {nsd_winnings_tourn:,.0f} Chips")

    st.divider()
    st.subheader("📈 Evolução Acumulada em Potes Grandes")

    # Prepara dataframe para o gráfico
    df_chart = (
        df_pnl
        .with_columns(pl.col("timestamp").str.slice(0, 10).alias("dia"))
        .group_by("dia")
        .agg(
            pl.col("net_profit").filter(pl.col("went_to_showdown") == True).sum().fill_null(0.0).alias("sd_lucro_diario"),
            pl.col("net_profit").filter(pl.col("went_to_showdown") == False).sum().fill_null(0.0).alias("nsd_lucro_diario")
        )
        .sort("dia")
        .with_columns(
            pl.col("sd_lucro_diario").cum_sum().alias("🔵 Linha Azul (Acumulado)"),
            pl.col("nsd_lucro_diario").cum_sum().alias("🔴 Linha Vermelha (Acumulado)")
        )
        .select(["dia", "🔵 Linha Azul (Acumulado)", "🔴 Linha Vermelha (Acumulado)"])
    )

    if df_chart.height > 0:
        pd_chart = df_chart.to_pandas()
        pd_chart.set_index("dia", inplace=True)
        st.line_chart(pd_chart, color=["#1E90FF", "#FF4B4B"])

    st.divider()

    # ==========================
    # TABELA DE PIORES PREJUÍZOS
    # ==========================
    st.subheader("🚨 Auditoria de Prejuízos Máximos")
    st.write("Mãos gigantes ordenadas do maior prejuízo para o menor. Analise os combos e o board.")

    # Obtém os vencedores e filtra o Hero
    from src.dashboard.domain_data import get_vencedores_df
    df_vencedores = get_vencedores_df(df).with_columns(
        pl.col("lista_vencedores").list.eval(pl.element().filter(pl.element() != "Hero")).list.join(", ").alias("winning_villain")
    ).select(["hand_id", "winning_villain"])

    # Cruzando com Hero Cards, Board, Vencedores e Cartas dos Vilões
    tabela_auditoria = (
        df_pnl
        .join(df_hero_cards, on="hand_id", how="left")
        .join(df_board, on="hand_id", how="left")
        .join(df_vencedores, on="hand_id", how="left")
        .join(df_villains_cards, on="hand_id", how="left")
        .select([
            "hand_id",
            "game_type",
            "winning_villain",
            "hero_cards",
            "villains_cards",
            "board",
            "went_to_showdown",
            "net_profit",
            "pot_in_bb"
        ])
        .sort("net_profit", descending=False) # Ascending = Maior prejuízo (negativo) no topo
    )

    st.dataframe(
        tabela_auditoria.to_pandas(),
        use_container_width=True,
        hide_index=True,
        column_config={
            "hand_id": "ID da Mão",
            "game_type": "Modalidade",
            "winning_villain": "Vilão Vencedor",
            "hero_cards": "Cartas do Herói",
            "villains_cards": "Cartas dos Vilões",
            "board": "Board (Cartas Comunitárias)",
            "went_to_showdown": "Showdown?",
            "net_profit": st.column_config.NumberColumn("Net Profit / Chips", format="%.2f"),
            "pot_in_bb": st.column_config.NumberColumn("Tamanho Pote (BB)", format="%.1f BB")
        }
    )

    from src.dashboard.domain_data import get_known_cards_df
    from src.dashboard.views.components.villain_explorer import render_villain_explorer
    
    df_known_cards = get_known_cards_df(df)
    render_villain_explorer(df, df_known_cards)
