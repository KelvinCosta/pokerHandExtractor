import streamlit as st
import polars as pl
from src.dashboard.domain_data import get_player_positions_df

def render_villain_explorer(df, df_known_cards):
    st.divider()
    st.subheader("🕵️‍♂️ Explorador de Range por Vilão e Posição")
    st.write("Busque por um vilão específico e veja exatamente com quais mãos e de quais posições ele foi para o Showdown. Ideal para anotações detalhadas de ranges.")

    # Traz a tabela de posições e faz o join com as mãos reveladas
    df_posicoes = get_player_positions_df(df)
    
    df_villain_ranges = (
        df_known_cards
        .unique(subset=["hand_id", "player"])
        .join(df_posicoes, on=["hand_id", "player"], how="left")
        .select(["player", "position", "hand_canonical", "combo", "hand_id"])
    )
    
    vilao_alvo = st.text_input("🔍 Buscar ID do Vilão (ex: 59f14cd7)", placeholder="Digite o hash do jogador...")
    
    if vilao_alvo:
        range_vilao = (
            df_villain_ranges
            .filter(pl.col("player").str.contains(vilao_alvo, literal=True))
            .sort(["hand_canonical", "position"])
        )
        
        if range_vilao.height > 0:
            st.success(f"Encontradas {range_vilao.height} mãos de Showdown para o jogador correspondente.")
            st.dataframe(
                range_vilao.to_pandas(),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "player": "Vilão",
                    "position": "Posição",
                    "hand_canonical": "Mão",
                    "combo": "Naipe",
                    "hand_id": "ID da Mão"
                }
            )
        else:
            st.warning("Nenhuma mão de Showdown encontrada para este ID.")
