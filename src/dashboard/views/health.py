import streamlit as st
import polars as pl
from src.dashboard.data_loader import load_tournaments

def render_health(df):
    st.title("❤️ Saúde Geral")
    st.write("Visão geral de lucratividade e volume de jogo da seleção atual.")

    # Total de Mãos
    total_maos = df.select("hand_id").n_unique()

    if total_maos == 0:
        st.warning("Nenhuma mão encontrada no período para o filtro atual.")
        return

    # Descobre o BB da mão e calcula finanças do Hero (Tudo em um único groupby ultra-rápido)
    lucro_por_mao = (
        df
        .group_by("hand_id")
        .agg(
            pl.col("amount").filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "POST")).max().fill_null(0.02).alias("bb_size"),
            pl.col("invested_amount").filter((pl.col("player") == "Hero") & (~pl.col("action_type").is_in(["COLLECT", "FOLD", "CHECK"]))).sum().fill_null(0.0).alias("investido"),
            pl.col("amount").filter((pl.col("player") == "Hero") & (pl.col("action_type") == "COLLECT")).sum().fill_null(0.0).alias("coletado"),
            pl.col("date").first().alias("timestamp"),
            pl.col("game_type").first().alias("game_type"),
            pl.col("game_info").first().alias("game_info")
        )
        .with_columns(
            (pl.col("coletado") - pl.col("investido")).alias("net_profit")
        )
        .with_columns(
            (pl.col("net_profit") / pl.col("bb_size")).alias("profit_in_bb")
        )
    )

    # 1. Lucro de Cash Games (apenas net_profit das mãos)
    tournament_types = ["Tournament", "Spin & Gold", "Mystery Battle Royale"]
    df_cash = lucro_por_mao.filter(~pl.col("game_type").is_in(tournament_types))
    cash_net_profit = df_cash["net_profit"].sum()
    
    # 2. Lucro de Torneios
    df_tournaments_hands = lucro_por_mao.filter(pl.col("game_type").is_in(tournament_types))
    tournament_net_profit = 0.0
    df_tournaments_daily = pl.DataFrame({"dia": [], "net_profit_diario": []}, schema={"dia": pl.Utf8, "net_profit_diario": pl.Float64})
    
    if df_tournaments_hands.height > 0:
        # Extrair tournament_id
        df_t = df_tournaments_hands.with_columns(
            pl.col("game_info").str.extract(r"Tournament #([0-9]+)").alias("tournament_id"),
            pl.col("timestamp").str.slice(0, 10).alias("dia")
        )
        
        # Mapear 1 dia por torneio (o primeiro dia que ele aparece)
        t_days = df_t.drop_nulls("tournament_id").group_by("tournament_id").agg(pl.col("dia").first())
        
        df_summaries = load_tournaments()
        if df_summaries.height > 0:
            df_summaries = df_summaries.with_columns(pl.col("tournament_id").cast(pl.Utf8))
            
            # Extrair data do nome do arquivo (ex: GG20260614)
            df_summaries = df_summaries.with_columns(
                pl.col("source_file").str.extract(r"GG(\d{8})").alias("raw_date")
            ).with_columns(
                (pl.col("raw_date").str.slice(0, 4) + "-" + pl.col("raw_date").str.slice(4, 2) + "-" + pl.col("raw_date").str.slice(6, 2)).alias("dia_file")
            )
            
            # Inferir game_type do arquivo para filtrar corretamente mesmo sem mãos associadas
            df_summaries = df_summaries.with_columns(
                pl.when(pl.col("source_file").str.contains("(?i)spin.?gold")).then(pl.lit("Spin & Gold"))
                .when(pl.col("source_file").str.contains("(?i)mystery battle royale")).then(pl.lit("Mystery Battle Royale"))
                .otherwise(pl.lit("Tournament")).alias("summary_game_type")
            )

            # Join FULL para manter torneios sem mãos exportadas (ex: flip&go onde não teve mão jogada)
            t_joined = t_days.join(df_summaries, on="tournament_id", how="full", coalesce=True)
            
            if t_joined.height > 0:
                t_joined = t_joined.with_columns(
                    pl.coalesce(["dia", "dia_file"]).alias("dia_oficial")
                ).drop_nulls("dia_oficial")
                
                # Aplicar filtro de game_type baseado no que o usuário selecionou na sidebar
                tipos_selecionados = st.session_state.get("game_type_filter", tournament_types)
                t_joined = t_joined.filter(pl.col("summary_game_type").is_in(tipos_selecionados))
                
                # Aplicar filtro de datas baseado no filtro exato da sidebar
                datas = st.session_state.get("date_filter")
                if datas and isinstance(datas, tuple) and len(datas) == 2:
                    min_dia_str = datas[0].strftime("%Y-%m-%d")
                    max_dia_str = datas[1].strftime("%Y-%m-%d")
                    t_joined = t_joined.filter(pl.col("dia_oficial").is_between(pl.lit(min_dia_str), pl.lit(max_dia_str)))
                
                t_joined = t_joined.fill_null(0.0).with_columns(
                    (pl.col("prize") - pl.col("buy_in")).alias("t_profit")
                )
                
                tournament_net_profit = t_joined["t_profit"].sum()
                
                # Agrupar por dia oficial para o gráfico
                df_tournaments_daily = t_joined.group_by("dia_oficial").agg(pl.col("t_profit").sum().alias("net_profit_diario")).rename({"dia_oficial": "dia"})

    total_net_profit = cash_net_profit + tournament_net_profit
    
    # Win rate: bb / 100 hands (geral em bb)
    total_profit_bb = lucro_por_mao["profit_in_bb"].sum()
    win_rate_bb100 = (total_profit_bb / total_maos) * 100

    col1, col2, col3 = st.columns(3)
    
    col1.metric("🃏 Total de Mãos", f"{total_maos:,}")
    
    col2.metric(
        "💵 Net Profit", 
        f"${total_net_profit:.2f}",
        delta=f"${total_net_profit:.2f}",
        delta_color="normal" if total_net_profit >= 0 else "inverse"
    )
    
    col3.metric(
        "📈 Win Rate (bb/100)", 
        f"{win_rate_bb100:.2f} bb",
        delta=f"{win_rate_bb100:.2f} bb",
        delta_color="normal" if win_rate_bb100 >= 0 else "inverse"
    )

    st.divider()
    
    st.subheader("📈 Evolução do Bankroll")
    
    grafico_cash = (
        df_cash
        .with_columns(pl.col("timestamp").str.slice(0, 10).alias("dia"))
        .group_by("dia")
        .agg(pl.col("net_profit").sum().alias("net_profit_diario"))
    )
    
    # Combinar o diário de Cash com o diário de Torneio
    grafico_df = pl.concat([grafico_cash, df_tournaments_daily]).group_by("dia").agg(pl.col("net_profit_diario").sum())
    
    grafico_df = (
        grafico_df
        .sort("dia")
        .with_columns(
            pl.col("net_profit_diario").cum_sum().alias("Net Profit Cumulativo ($)")
        )
    )
    
    # Streamlit line chart
    if grafico_df.height > 0:
        pd_grafico = grafico_df.select(["dia", "Net Profit Cumulativo ($)"]).to_pandas()
        pd_grafico.set_index("dia", inplace=True)
        st.line_chart(pd_grafico)
