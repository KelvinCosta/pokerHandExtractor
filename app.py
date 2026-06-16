import streamlit as st
import polars as pl
from src.dashboard.data_loader import get_base_dataframe
from src.dashboard.views.sidebar import render_sidebar
from src.dashboard.views.overview import render_overview
from src.dashboard.views.villains import render_villains, get_df_viloes
from src.dashboard.views.rivalry import render_rivalry
from src.dashboard.views.river_audit import render_river_audit
from src.dashboard.views.cbet_audit import render_cbet_audit

st.set_page_config(layout="wide")
st.title("📊 Poker Telemetry Dashboard (RnC NL2)")

# Carrega os dados brutos
df, nome_coluna_data = get_base_dataframe()

# Aplica os filtros da Sidebar
df_clean = render_sidebar(df, nome_coluna_data)

# Prepara DataFrames auxiliares reutilizados por múltiplas Views
hero_cards_df = (
    df_clean
    .select(["hand_id", "player_cards"])
    .drop_nulls(subset=["player_cards"])
    .unique(subset=["hand_id"]) 
    .explode("player_cards")
    .unnest("player_cards")
    .filter(pl.col("player") == "Hero")
    .select(["hand_id", pl.col("cards").alias("hero_cards")])
)

board_df = (
    df_clean
    .select(["hand_id", "board_cards"])
    .drop_nulls(subset=["board_cards"])
    .unique(subset=["hand_id"])
    .with_columns(
        pl.col("board_cards").list.unique(maintain_order=True).list.join(" ").alias("board")
    )
    .select(["hand_id", "board"])
)

df_viloes = get_df_viloes(df_clean)

# Renderiza os Módulos Lineares
render_overview(df_clean)

df_tags = render_villains(df_clean, df_viloes, board_df)

render_rivalry(df_clean, df_viloes, df_tags)

st.divider()
st.subheader("River Sizing EV Delta")
render_river_audit(df_clean, hero_cards_df, board_df)

render_cbet_audit(df_clean, hero_cards_df, board_df)