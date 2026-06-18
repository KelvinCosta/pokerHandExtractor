import streamlit as st
import polars as pl
from src.dashboard.domain_data import process_hand_data, get_player_positions_df

def render_population_range(df):
    st.divider()
    st.title("👥 População e Ranges (MDA)")
    st.write("Análise Massiva de Dados (MDA) focada em mapear as tendências do Field no Showdown e os seus padrões de Call.")

    # 1. Preparação dos dados: Extração das cartas dos vilões conhecidas (no showdown)
    # Pegamos apenas ações onde o player != Hero e ele tem player_cards != nulo.
    # df tem player_cards como List[Struct] com keys: "player", "cards".
    # Usaremos um lazy-mapping para transformar no formato canônico.
    
    st.info("💡 Extraindo mãos canônicas (ex: 'AKs', 'AA') a partir das cartas da população. O cálculo é feito de forma nativa e em tempo real apenas nos cenários alvo.")

    df_known_cards = (
        df.filter((pl.col("player") != "Hero") & (pl.col("player_cards").is_not_null()))
        .with_columns(
            pl.struct(["player_cards", "player"])
            .map_elements(lambda x: process_hand_data(x["player_cards"], x["player"]), return_dtype=pl.Struct({"combo": pl.Utf8, "hand_canonical": pl.Utf8}))
            .alias("cards_info")
        )
        .unnest("cards_info")
        .filter(pl.col("hand_canonical").is_not_null())
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏁 Top 20 Mãos Gerais da População (Showdown)")
        st.write("Quais são as mãos que os Vilões mais frequentemente levam para o Showdown? Isso desenha o **Range Real** da população no fim da linha.")
        
        todas_as_maos = (
            df_known_cards
            .unique(subset=["hand_id", "player", "hand_canonical"])
            .group_by("hand_canonical")
            .agg(pl.len().alias("vezes_visto"))
            .sort("vezes_visto", descending=True)
            .head(20)
        )
        
        if todas_as_maos.height > 0:
            st.dataframe(
                todas_as_maos.to_pandas(), 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "hand_canonical": st.column_config.TextColumn("Mão Canônica"),
                    "vezes_visto": st.column_config.ProgressColumn("Frequência", format="%d", min_value=0, max_value=todas_as_maos["vezes_visto"].max())
                }
            )
        else:
            st.warning("Sem dados suficientes de Showdown da população.")

    with col2:
        st.subheader("🎣 O que eles seguram quando dão CALL no River?")
        st.write("Saber a distribuição das cartas quando o Field decide **pagar** a última aposta te ajuda a saber quando você está sendo 'Value Owned' ou se eles pagam muito largo.")
        
        river_calls = (
            df_known_cards
            .filter((pl.col("street") == "RIVER") & (pl.col("action_type") == "CALL"))
            .group_by("hand_canonical")
            .agg(pl.len().alias("vezes_pago"))
            .sort("vezes_pago", descending=True)
            .head(20)
        )
        
        if river_calls.height > 0:
            st.dataframe(
                river_calls.to_pandas(), 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "hand_canonical": st.column_config.TextColumn("Mão Canônica"),
                    "vezes_pago": st.column_config.ProgressColumn("Frequência", format="%d", min_value=0, max_value=river_calls["vezes_pago"].max())
                }
            )
        else:
            st.warning("Nenhum Call no River registrado com cartas conhecidas do Vilão.")

    st.divider()
    st.subheader("💎 Detalhamento de Combo Específico (População)")
    
    opcoes_maos = sorted(df_known_cards["hand_canonical"].unique().to_list()) if df_known_cards.height > 0 else []
    
    if opcoes_maos:
        col_selecao, col_tabela = st.columns([1, 2])
        
        with col_selecao:
            combo_alvo = st.selectbox("Selecione a Mão Canônica (Ex: AA, AKs)", options=opcoes_maos)
            st.caption("Veja as frequências das combinações exatas (Naipes) para esta mão.")
            
        with col_tabela:
            combo_details = (
                df_known_cards
                .filter(pl.col("hand_canonical") == combo_alvo)
                .unique(subset=["hand_id", "player", "combo"])
                .group_by("combo")
                .agg(pl.len().alias("vezes_visto"))
                .sort("vezes_visto", descending=True)
            )
            
            st.dataframe(
                combo_details.to_pandas(), 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "combo": "Combinação (Naipes)",
                    "vezes_visto": "Frequência Absoluta"
                }
            )

    from src.dashboard.views.components.villain_explorer import render_villain_explorer
    render_villain_explorer(df, df_known_cards)

