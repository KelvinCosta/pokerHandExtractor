import streamlit as st
import polars as pl
import plotly.express as px

def render_preflop(df):
    st.title("🔥 Motor Pré-Flop")
    st.write("Estatísticas de VPIP, PFR e 3-Bet para avaliar o perfil de agressividade pré-flop do Hero.")

    # Filtra apenas o pré-flop
    df_pf = df.filter(pl.col("street") == "PRE_FLOP")

    # Identificar mãos únicas jogadas (Total de Mãos)
    total_maos = df.select("hand_id").n_unique()

    if total_maos == 0:
        st.warning("Nenhuma mão encontrada no período.")
        return

    # Adicionar contagem cumulativa de Raises na mão para identificar 3-bets
    # Como as ações mantêm a ordem cronológica do Parquet, cum_sum() conta os raises até aquele momento
    df_pf = df_pf.with_columns(
        pl.col("action_type").eq("RAISE").cum_sum().over("hand_id").alias("raises_so_far")
    )

    # Identificar métricas do Hero
    # VPIP: Hero deu CALL ou RAISE no Pré-flop
    vpip_hands = (
        df_pf
        .filter((pl.col("player") == "Hero") & (pl.col("action_type").is_in(["CALL", "RAISE"])))
        .select("hand_id")
        .n_unique()
    )

    # PFR: Hero deu RAISE no Pré-flop
    pfr_hands = (
        df_pf
        .filter((pl.col("player") == "Hero") & (pl.col("action_type") == "RAISE"))
        .select("hand_id")
        .n_unique()
    )

    # 3-Bet: Hero deu RAISE e foi o segundo (ou mais) RAISE da mão (raises_so_far >= 2)
    three_bet_hands = (
        df_pf
        .filter((pl.col("player") == "Hero") & (pl.col("action_type") == "RAISE") & (pl.col("raises_so_far") >= 2))
        .select("hand_id")
        .n_unique()
    )

    vpip_pct = (vpip_hands / total_maos) * 100
    pfr_pct = (pfr_hands / total_maos) * 100
    three_bet_pct = (three_bet_hands / total_maos) * 100
    
    # Gap VPIP/PFR
    gap = vpip_pct - pfr_pct

    # Definir o perfil do jogador
    if vpip_pct > 35:
        perfil = "Maniac / Loose-Aggressive (LAG)" if pfr_pct > 25 else "Loose-Passive (Calling Station)"
    elif 20 <= vpip_pct <= 35:
        perfil = "TAG (Tight-Aggressive) / Regular" if pfr_pct >= 15 else "Tight-Passive"
    else:
        perfil = "Nit (Pedra)"

    st.subheader(f"🧠 Perfil Identificado: {perfil}")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🃏 Total de Mãos", f"{total_maos:,}")
    col2.metric("🎯 VPIP", f"{vpip_pct:.1f}%", help="Voluntarily Put in Pot: Mãos que o Hero pagou ou aumentou voluntariamente.")
    col3.metric("⚔️ PFR", f"{pfr_pct:.1f}%", help="Pre-Flop Raise: Mãos que o Hero aumentou antes do Flop.")
    col4.metric("🧨 3-Bet", f"{three_bet_pct:.1f}%", help="Mãos em que o Hero fez uma re-aumentou (3-Bet) pré-flop.")

    st.divider()

    col_grafico, col_texto = st.columns([2, 1])

    with col_grafico:
        st.subheader("Relação VPIP x PFR")
        # Gráfico de barras simples usando o nativo do Streamlit
        grafico_df = pl.DataFrame({
            "Métrica": ["VPIP", "PFR", "Gap (Call)"],
            "Porcentagem (%)": [vpip_pct, pfr_pct, gap]
        })
        
        # Convertendo para Pandas e setando o index para o gráfico nativo do Streamlit ler bonito
        pd_grafico = grafico_df.to_pandas().set_index("Métrica")
        st.bar_chart(pd_grafico, color=["#ff4b4b"])

    with col_texto:
        st.subheader("Diagnóstico do Motor")
        st.write(f"- **VPIP ({vpip_pct:.1f}%):** Mede a frequência que você joga uma mão. O ideal no 6-max costuma ser entre 22% e 28%.")
        st.write(f"- **PFR ({pfr_pct:.1f}%):** Mede a sua agressividade. Deve estar próximo do VPIP (gap pequeno).")
        st.write(f"- **Gap ({gap:.1f}%):** O ideal é manter o Gap abaixo de 5%. Um Gap muito alto indica que você dá muito 'Call' passivo pré-flop (Calling Station).")
        st.write(f"- **3-Bet ({three_bet_pct:.1f}%):** Frequência global de 3-bet. O ideal é ficar entre 6% a 10%.")
