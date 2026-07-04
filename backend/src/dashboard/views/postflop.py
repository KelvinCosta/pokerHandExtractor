import streamlit as st
import polars as pl

def render_postflop(df):
    st.title("⚔️ Agressão Pós-Flop")
    st.write("Estatísticas avançadas de Continuação de Aposta (C-Bet) e efetividade em Showdowns.")

    # 1. Base Geral
    # Mãos em que o Hero viu o Flop
    hands_hero_saw_flop = (
        df.filter((pl.col("player") == "Hero") & (pl.col("street") == "FLOP"))
        .select("hand_id").unique()
    )
    
    if hands_hero_saw_flop.height == 0:
        st.warning("Nenhuma mão com Flop vista pelo Hero no período.")
        return

    # Descobrir quem foi o Último Agressor Pré-Flop (PFR)
    last_preflop_raise = (
        df.filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "RAISE"))
        .group_by("hand_id")
        .agg(pl.col("player").last().alias("last_aggressor"))
    )

    # Descobrir quem deu o Primeiro Bet no Flop
    first_flop_bet = (
        df.filter((pl.col("street") == "FLOP") & (pl.col("action_type") == "BET"))
        .group_by("hand_id")
        .agg(pl.col("player").first().alias("first_bettor"))
    )

    # Pegar a primeira ação do Hero no Flop
    hero_first_flop_action = (
        df.filter((pl.col("player") == "Hero") & (pl.col("street") == "FLOP"))
        .group_by("hand_id")
        .agg(pl.col("action_type").first().alias("hero_first_action"))
    )

    # Consolidar Oportunidades Pós-Flop
    flop_situations = (
        hands_hero_saw_flop
        .join(last_preflop_raise, on="hand_id", how="left")
        .join(first_flop_bet, on="hand_id", how="left")
        .join(hero_first_flop_action, on="hand_id", how="left")
    )

    # -------------------------------------------------------------
    # 2. C-Bet Flop
    # Oportunidade: Hero foi PFR e (Hero foi o primeiro a agir OU Hero apostou primeiro)
    cbet_opp_df = flop_situations.filter(
        (pl.col("last_aggressor") == "Hero") & 
        (pl.col("hero_first_action").is_in(["BET", "CHECK"]))
    )
    cbet_opp_count = cbet_opp_df.height

    # Sucesso: Hero C-Betou (A primeira ação foi BET)
    cbet_success_count = cbet_opp_df.filter(pl.col("hero_first_action") == "BET").height

    cbet_pct = (cbet_success_count / cbet_opp_count * 100) if cbet_opp_count > 0 else 0.0

    # -------------------------------------------------------------
    # 3. Fold to C-Bet
    # Oportunidade: Vilão foi PFR e Vilão C-Betou (fez o first bet), Hero viu o Flop
    fold_cbet_opp_df = flop_situations.filter(
        (pl.col("last_aggressor") != "Hero") & 
        (pl.col("last_aggressor").is_not_null()) &
        (pl.col("first_bettor") == pl.col("last_aggressor"))
    )
    fold_cbet_opp_count = fold_cbet_opp_df.height

    # Sucesso: Hero Foldou em algum momento no Flop
    hero_folded_flop = (
        df.filter((pl.col("player") == "Hero") & (pl.col("street") == "FLOP") & (pl.col("action_type") == "FOLD"))
        .select("hand_id").unique()
    )
    
    fold_cbet_success_count = fold_cbet_opp_df.join(hero_folded_flop, on="hand_id", how="inner").height

    fold_cbet_pct = (fold_cbet_success_count / fold_cbet_opp_count * 100) if fold_cbet_opp_count > 0 else 0.0

    # -------------------------------------------------------------
    # 4. WSD (Went to Showdown)
    # Oportunidade: Hero viu o Flop
    wsd_opp_count = hands_hero_saw_flop.height

    # Identificar Mãos com Showdown (mais de um player mostrou cartas)
    showdown_hands = (
        df.select(["hand_id", "player_cards"]).unique()
        .filter(pl.col("player_cards").list.len() > 1)
        .select("hand_id")
    )
    
    # Identificar Mãos em que Hero foldou (em qualquer street)
    hero_folded_any = (
        df.filter((pl.col("player") == "Hero") & (pl.col("action_type") == "FOLD"))
        .select("hand_id").unique()
    )

    # WSD Success: Teve Showdown E Hero NÃO foldou
    hero_went_to_sd = (
        showdown_hands
        .join(hands_hero_saw_flop, on="hand_id", how="inner")
        .join(hero_folded_any, on="hand_id", how="anti")
    )
    wsd_success_count = hero_went_to_sd.height

    wsd_pct = (wsd_success_count / wsd_opp_count * 100) if wsd_opp_count > 0 else 0.0

    # -------------------------------------------------------------
    # 5. W$SD (Won Money at Showdown)
    # Oportunidade: Hero foi pro Showdown
    wsd_money_opp = wsd_success_count

    # Success: Hero coletou dinheiro do pote
    hero_won_money = (
        df.filter((pl.col("player") == "Hero") & (pl.col("action_type") == "COLLECT"))
        .select("hand_id").unique()
    )
    
    wssd_success_count = hero_went_to_sd.join(hero_won_money, on="hand_id", how="inner").height

    wssd_pct = (wssd_success_count / wsd_money_opp * 100) if wsd_money_opp > 0 else 0.0

    # -------------------------------------------------------------
    # 6. SD & Non-SD Winnings
    df_hero_investido = (
        df.filter(
            (pl.col("player") == "Hero") & 
            (~pl.col("action_type").is_in(["COLLECT", "FOLD", "CHECK"]))
        )
        .group_by("hand_id")
        .agg(pl.col("invested_amount").sum().fill_null(0.0).alias("hero_colocou"))
    )

    df_hero_ganhou = (
        df.filter((pl.col("player") == "Hero") & (pl.col("action_type") == "COLLECT"))
        .group_by("hand_id")
        .agg(pl.col("amount").sum().fill_null(0.0).alias("hero_puxou"))
    )

    df_hero_pnl = (
        df.filter(pl.col("player") == "Hero")
        .select("hand_id").unique()
        .join(df_hero_investido, on="hand_id", how="left")
        .join(df_hero_ganhou, on="hand_id", how="left")
        .fill_null(0.0)
        .with_columns(
            (pl.col("hero_puxou") - pl.col("hero_colocou")).alias("net_profit")
        )
    )

    # Cálculo do tamanho do pote em BBs
    df_pot_sizes = (
        df.group_by("hand_id")
        .agg(
            pl.col("total_pot_final").first().alias("pot_size_usd"),
            pl.col("amount").filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "POST")).max().fill_null(0.02).alias("bb_size")
        )
        .with_columns(
            (pl.col("pot_size_usd") / pl.col("bb_size")).alias("pot_in_bb")
        )
    )

    df_hero_pnl = df_hero_pnl.join(df_pot_sizes, on="hand_id", how="left")

    # ==========================================
    # RENDERIZAÇÃO
    # ==========================================
    
    st.markdown("### 📊 Frequências e Agressividade")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 C-Bet Flop", f"{cbet_pct:.1f}%", help=f"Fez C-Bet {cbet_success_count} vezes de {cbet_opp_count} oportunidades.")
    with col2:
        st.metric("🛡️ Fold to C-Bet", f"{fold_cbet_pct:.1f}%", help=f"Foldou {fold_cbet_success_count} vezes de {fold_cbet_opp_count} oportunidades.")
    with col3:
        st.metric("👁️ WSD (Went to Showdown)", f"{wsd_pct:.1f}%", help=f"Chegou no Showdown em {wsd_success_count} mãos de {wsd_opp_count} flops vistos.")
    with col4:
        st.metric("💰 W$SD (Won $ at Showdown)", f"{wssd_pct:.1f}%", help=f"Venceu {wssd_success_count} vezes nas {wsd_money_opp} vezes que foi ao Showdown.")

    st.markdown("### 💵 Linhas Financeiras")
    filtro_potes_grandes = st.checkbox("🔥 Isolar Potes Gigantes (Pote Final ≥ 40 BBs)", help="Analisa a linha azul e vermelha apenas nas mãos onde o pote inflou consideravelmente.")
    
    if filtro_potes_grandes:
        df_hero_pnl_filtrado = df_hero_pnl.filter(pl.col("pot_in_bb") >= 40.0)
    else:
        df_hero_pnl_filtrado = df_hero_pnl

    # Precisamos pegar o game_type de volta para df_hero_pnl_filtrado
    df_game_types = df.select(["hand_id", "game_type"]).unique()
    df_hero_pnl_filtrado = df_hero_pnl_filtrado.join(df_game_types, on="hand_id", how="left")

    tournament_types = ["Tournament", "Spin & Gold", "Mystery Battle Royale"]
    
    # Linhas para Cash Game
    df_cash_pnl = df_hero_pnl_filtrado.filter(~pl.col("game_type").is_in(tournament_types))
    if df_cash_pnl.height > 0:
        st.write("#### 💰 Cash Game ($)")
        sd_winnings_cash = df_cash_pnl.join(showdown_hands, on="hand_id", how="inner")["net_profit"].sum()
        nsd_winnings_cash = df_cash_pnl.join(showdown_hands, on="hand_id", how="anti")["net_profit"].sum()
        col_sd, col_nsd = st.columns(2)
        with col_sd:
            st.info(f"**🔵 SD Winnings (Linha Azul)**\n\n### ${sd_winnings_cash:.2f}")
        with col_nsd:
            st.error(f"**🔴 Non-SD Winnings (Linha Vermelha)**\n\n### ${nsd_winnings_cash:.2f}")

    # Linhas para Torneio
    df_tourn_pnl = df_hero_pnl_filtrado.filter(pl.col("game_type").is_in(tournament_types))
    if df_tourn_pnl.height > 0:
        st.write("#### 🏆 Torneios (Net Chips)")
        sd_winnings_tourn = df_tourn_pnl.join(showdown_hands, on="hand_id", how="inner")["net_profit"].sum()
        nsd_winnings_tourn = df_tourn_pnl.join(showdown_hands, on="hand_id", how="anti")["net_profit"].sum()
        col_sd_t, col_nsd_t = st.columns(2)
        with col_sd_t:
            st.info(f"**🔵 SD Winnings (Linha Azul)**\n\n### {sd_winnings_tourn:,.0f} Chips")
        with col_nsd_t:
            st.error(f"**🔴 Non-SD Winnings (Linha Vermelha)**\n\n### {nsd_winnings_tourn:,.0f} Chips")

    st.divider()

    st.subheader("🕵️‍♂️ Auditoria de Linhas (Showdown vs Non-Showdown)")
    st.write("Analise as mãos exatas que estão movimentando suas linhas, junto com as maiores Pot Odds que você enfrentou.")

    # Mãos de Showdown (Linha Azul)
    df_blue = df_hero_pnl_filtrado.join(showdown_hands, on="hand_id", how="inner")
    
    # Mãos de Non-Showdown (Linha Vermelha)
    df_red = df_hero_pnl_filtrado.join(showdown_hands, on="hand_id", how="anti")

    # Juntar todas e classificar
    df_blue = df_blue.with_columns(pl.lit("🔵 Azul (Showdown)").alias("linha_impactada"))
    df_red = df_red.with_columns(pl.lit("🔴 Vermelha (Non-SD)").alias("linha_impactada"))
    
    df_audit = pl.concat([df_blue, df_red]).sort("net_profit", descending=False)

    # Verifica se as colunas de pot odds já existem (para não quebrar caso o datalake ainda não tenha sido atualizado)
    cols_meta = ["hand_id", "hero_cards", "board_str"]
    if "hero_flop_pot_odds" in df.columns:
        cols_meta.extend(["hero_flop_pot_odds", "hero_turn_pot_odds", "hero_river_pot_odds"])

    # Obter os metadados (cartas e odds) da tabela base
    df_meta = (
        df.filter(pl.col("player") == "Hero")
        .select(cols_meta)
        .unique(subset=["hand_id"])
    )

    df_audit = df_audit.join(df_meta, on="hand_id", how="left")

    col_config = {
        "hand_id": "ID da Mão",
        "game_type": "Modalidade",
        "linha_impactada": "Linha",
        "net_profit": st.column_config.NumberColumn("Net Profit / Chips", format="%.2f"),
        "hero_cards": "Cartas do Herói",
        "board_str": "Board"
    }
    
    col_order = ["hand_id", "game_type", "linha_impactada", "net_profit", "hero_cards", "board_str"]

    if "hero_flop_pot_odds" in df.columns:
        col_config.update({
            "hero_flop_pot_odds": st.column_config.NumberColumn("Flop Pot Odds", format="%.1f%%"),
            "hero_turn_pot_odds": st.column_config.NumberColumn("Turn Pot Odds", format="%.1f%%"),
            "hero_river_pot_odds": st.column_config.NumberColumn("River Pot Odds", format="%.1f%%")
        })
        col_order.extend(["hero_flop_pot_odds", "hero_turn_pot_odds", "hero_river_pot_odds"])

    st.dataframe(
        df_audit.to_pandas(),
        use_container_width=True,
        hide_index=True,
        column_config=col_config,
        column_order=col_order
    )

    st.divider()

    st.subheader("🩺 Diagnóstico do Pós-Flop")
    
    with st.expander("Ver Análise de Texto Completa", expanded=True):
        diag_cbet = "Agressividade ideal." if 50 <= cbet_pct <= 70 else ("Muito passivo (Deixa os oponentes realizarem equidade de graça)." if cbet_pct < 50 else "Agressivo demais (Pode ser explorado por check-raises).")
        st.write(f"- **C-Bet Flop ({cbet_pct:.1f}%):** O padrão vencedor em Cash Games 6-max gira em torno de 50% a 70%. **Diagnóstico:** {diag_cbet}")

        diag_fcbet = "Frequência sólida." if 40 <= fold_cbet_pct <= 50 else ("Você está pagando demais (Calling Station)." if fold_cbet_pct < 40 else "Foldando muito fácil (Overfolding).")
        st.write(f"- **Fold to C-Bet ({fold_cbet_pct:.1f}%):** Um jogador balanceado folda entre 40% e 50% das vezes. **Diagnóstico:** {diag_fcbet}")

        diag_wsd = "Seleção de mãos excelente." if 25 <= wsd_pct <= 32 else ("Chegando muito ao Showdown com mãos fracas." if wsd_pct > 32 else "Blefando muito ou foldando demais antes do River.")
        st.write(f"- **WSD ({wsd_pct:.1f}%):** Mede quão 'teimoso' você é após o Flop. O ideal (PokerTracker) é 25% a 32%. **Diagnóstico:** {diag_wsd}")

        diag_wssd = "Monstro dos Showdowns!" if wssd_pct >= 50 else "Perdendo dinheiro nos potes grandes. Reavalie seus calls no River."
        st.write(f"- **W$SD ({wssd_pct:.1f}%):** Se este valor estiver abaixo de 50%, significa que você está indo para o Showdown perdendo. O ideal é 50% ou mais. **Diagnóstico:** {diag_wssd}")
