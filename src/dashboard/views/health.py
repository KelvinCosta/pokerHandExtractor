import streamlit as st
import polars as pl

def render_health(df):
    st.title("❤️ Saúde Geral")
    st.write("Visão geral de lucratividade e volume de jogo (Apenas Cash Games - Rush & Cash).")

    # Filtra apenas Cash Games (Começam com RC)
    df_cash = df.filter(pl.col("hand_id").str.starts_with("RC"))

    # Total de Mãos
    total_maos = df_cash.select("hand_id").n_unique()

    if total_maos == 0:
        st.warning("Nenhuma mão de Cash Game (Rush & Cash) encontrada no período.")
        return

    # Descobre o BB (Big Blind) de cada mão pegando o maior POST no pré-flop
    bb_df = (
        df_cash
        .filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "POST"))
        .group_by("hand_id")
        .agg(pl.col("amount").max().alias("bb_size"))
    )

    # Investimento do Hero por mão
    investimento_df = (
        df_cash
        .filter((pl.col("player") == "Hero") & (~pl.col("action_type").is_in(["COLLECT", "FOLD", "CHECK"])))
        .group_by("hand_id")
        .agg(pl.col("amount").sum().alias("investido"))
    )

    # Retorno (Coleta) do Hero por mão
    retorno_df = (
        df_cash
        .filter((pl.col("player") == "Hero") & (pl.col("action_type") == "COLLECT"))
        .group_by("hand_id")
        .agg(pl.col("amount").sum().alias("coletado"))
    )

    # Junta tudo para calcular o Net Profit por mão
    lucro_por_mao = (
        pl.DataFrame({"hand_id": df_cash["hand_id"].unique()})
        .join(investimento_df, on="hand_id", how="left").fill_null(0.0)
        .join(retorno_df, on="hand_id", how="left").fill_null(0.0)
        .join(bb_df, on="hand_id", how="left").fill_null(0.02) # fallback para NL2
        .with_columns(
            (pl.col("coletado") - pl.col("investido")).alias("net_profit")
        )
        .with_columns(
            (pl.col("net_profit") / pl.col("bb_size")).alias("profit_in_bb")
        )
    )

    total_net_profit = lucro_por_mao["net_profit"].sum()
    total_profit_bb = lucro_por_mao["profit_in_bb"].sum()
    
    # Win rate: bb / 100 hands
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
    
    # Prepara dados acumulados para o gráfico
    tempo_df = (
        df_cash
        .group_by("hand_id")
        .agg(pl.col("date").first().alias("timestamp"))
    )

    grafico_df = (
        lucro_por_mao
        .join(tempo_df, on="hand_id", how="inner")
        .sort("timestamp")
        .with_columns(
            pl.col("net_profit").cum_sum().alias("Net Profit Cumulativo ($)")
        )
    )
    
    # Streamlit line chart
    if grafico_df.height > 0:
        pd_grafico = grafico_df.select(["timestamp", "Net Profit Cumulativo ($)"]).to_pandas()
        pd_grafico.set_index("timestamp", inplace=True)
        st.line_chart(pd_grafico)
