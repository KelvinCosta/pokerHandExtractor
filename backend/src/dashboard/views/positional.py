import streamlit as st
import polars as pl
from src.dashboard.domain_data import get_player_positions_df

def render_positional(df):
    st.title("🪑 Consciência Posicional")
    st.write("Análise detalhada do seu desempenho e agressividade isolado por cadeira ocupada.")

    # Obter as posições do Hero
    df_posicoes = get_player_positions_df(df)
    hero_positions = df_posicoes.filter(pl.col("player") == "Hero").select(["hand_id", "position"])

    if hero_positions.height == 0:
        st.warning("Nenhuma mão com posição do Hero identificada no período.")
        return

    # Total de mãos jogadas pelo Hero
    todas_maos_hero = df.filter(pl.col("player") == "Hero").select("hand_id").unique()
    
    # 1. PnL do Hero em BB
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

    df_bb_size = (
        df.filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "POST"))
        .group_by("hand_id")
        .agg(pl.col("amount").max().fill_null(0.02).alias("bb_size"))
    )

    df_hero_pnl = (
        todas_maos_hero
        .join(df_hero_investido, on="hand_id", how="left")
        .join(df_hero_ganhou, on="hand_id", how="left")
        .join(df_bb_size, on="hand_id", how="left")
        .fill_null(0.0)
        .with_columns(
            pl.when(pl.col("bb_size") > 0)
            .then((pl.col("hero_puxou") - pl.col("hero_colocou")) / pl.col("bb_size"))
            .otherwise(0.0)
            .alias("profit_bb")
        )
    )

    # 2. VPIP e PFR
    preflop_hero = df.filter((pl.col("player") == "Hero") & (pl.col("street") == "PRE_FLOP"))
    
    vpip_hands = (
        preflop_hero.filter(pl.col("action_type").is_in(["CALL", "RAISE"]))
        .select("hand_id").unique()
        .with_columns(pl.lit(1).alias("is_vpip"))
    )
    
    pfr_hands = (
        preflop_hero.filter(pl.col("action_type") == "RAISE")
        .select("hand_id").unique()
        .with_columns(pl.lit(1).alias("is_pfr"))
    )

    # 3. Flop View
    flop_hands = (
        df.filter((pl.col("player") == "Hero") & (pl.col("street") == "FLOP"))
        .select("hand_id").unique()
        .with_columns(pl.lit(1).alias("saw_flop"))
    )

    # 4. Showdown (WSD)
    # Mãos que foram pro showdown
    showdown_hands = (
        df.select(["hand_id", "player_cards"]).unique()
        .filter(pl.col("player_cards").list.len() > 1)
        .select("hand_id")
    )
    # Mãos em que o hero foldou (qualquer momento)
    hero_folded_any = (
        df.filter((pl.col("player") == "Hero") & (pl.col("action_type") == "FOLD"))
        .select("hand_id").unique()
    )
    # WSD Success: Viu flop, teve showdown e não foldou
    went_to_sd_hands = (
        flop_hands.select("hand_id")
        .join(showdown_hands, on="hand_id", how="inner")
        .join(hero_folded_any, on="hand_id", how="anti")
        .with_columns(pl.lit(1).alias("went_to_sd"))
    )

    # Consolidar todas as métricas na base hero_positions
    df_consolidado = (
        hero_positions
        .join(df_hero_pnl.select(["hand_id", "profit_bb"]), on="hand_id", how="left")
        .join(vpip_hands, on="hand_id", how="left")
        .join(pfr_hands, on="hand_id", how="left")
        .join(flop_hands, on="hand_id", how="left")
        .join(went_to_sd_hands, on="hand_id", how="left")
        .fill_null(0)
    )

    # Agrupar por posição
    df_agg = (
        df_consolidado.group_by("position")
        .agg(
            pl.len().alias("hands"),
            pl.col("profit_bb").sum().alias("total_profit_bb"),
            pl.col("is_vpip").sum().alias("vpip_count"),
            pl.col("is_pfr").sum().alias("pfr_count"),
            pl.col("saw_flop").sum().alias("flop_count"),
            pl.col("went_to_sd").sum().alias("sd_count"),
        )
        .with_columns(
            (pl.col("vpip_count") / pl.col("hands") * 100).alias("vpip_pct"),
            (pl.col("pfr_count") / pl.col("hands") * 100).alias("pfr_pct"),
            (pl.col("flop_count") / pl.col("hands") * 100).alias("flop_view_pct"),
            pl.when(pl.col("flop_count") > 0)
            .then(pl.col("sd_count") / pl.col("flop_count") * 100)
            .otherwise(0.0)
            .alias("wsd_pct")
        )
    )

    # Ordenar pelas posições conhecidas
    ordem_posicoes = {"BTN": 1, "CO": 2, "MP": 3, "UTG": 4, "EP1": 5, "EP2": 6, "EP3": 7, "SB": 8, "BB": 9, "UNK": 10}
    df_agg = df_agg.with_columns(
        pl.col("position").replace_strict(ordem_posicoes, default=99).alias("ordem")
    ).sort("ordem").drop("ordem")

    st.subheader("📊 Métricas Consolidadas")
    
    col_config = {
        "position": "Posição",
        "hands": "Mãos Jogadas",
        "total_profit_bb": st.column_config.NumberColumn("Lucro (BB)", format="%.2f BB"),
        "vpip_pct": st.column_config.NumberColumn("VPIP %", format="%.1f%%"),
        "pfr_pct": st.column_config.NumberColumn("PFR %", format="%.1f%%"),
        "flop_view_pct": st.column_config.NumberColumn("Flop View %", format="%.1f%%"),
        "wsd_pct": st.column_config.NumberColumn("WSD (Showdown) %", format="%.1f%%"),
    }
    
    df_display = df_agg.select([
        "position", "hands", "total_profit_bb", "vpip_pct", "pfr_pct", "flop_view_pct", "wsd_pct"
    ])
    
    st.dataframe(
        df_display.to_pandas(),
        use_container_width=True,
        hide_index=True,
        column_config=col_config
    )

    st.divider()
    st.write("💡 **Dica Analítica:** Jogadores lucrativos tendem a ganhar a maior parte de seu dinheiro no Button (BTN) e Cutoff (CO), onde possuem vantagem posicional no pós-flop. As posições iniciais (UTG, MP) e as blinds (SB, BB) geralmente operam com ranges mais restritos ou até perdas controladas (no caso do BB).")
