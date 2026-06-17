import streamlit as st
import polars as pl
from src.dashboard.data_loader import get_base_dataframe
from src.dashboard.views.sidebar import render_sidebar
from src.dashboard.views.overview import render_overview
from src.dashboard.views.villains import render_villains, get_df_viloes
from src.dashboard.views.rivalry import render_rivalry
from src.dashboard.views.river_audit import render_river_audit
from src.dashboard.views.cbet_audit import render_cbet_audit
from src.dashboard.views.health import render_health

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

from src.dashboard.config import carregar_tags

# Função para fornecer o df_tags para as páginas que precisam dele
def get_df_tags():
    dicionario_tags = carregar_tags()
    if dicionario_tags:
        return pl.DataFrame({"player": list(dicionario_tags.keys()), "notas_vilao": list(dicionario_tags.values())})
    return pl.DataFrame({"player": [], "notas_vilao": []}, schema={"player": pl.Utf8, "notas_vilao": pl.Utf8})

# Define as páginas
def page_health():
    render_health(df_clean)

def page_overview():
    render_overview(df_clean)

def page_villains():
    # O retorno é descartado pois a navegação gerencia o estado das páginas
    _ = render_villains(df_clean, df_viloes, board_df)

def page_rivalry():
    df_tags = get_df_tags()
    render_rivalry(df_clean, df_viloes, df_tags)

def page_river():
    st.divider()
    st.subheader("River Sizing EV Delta")
    render_river_audit(df_clean, hero_cards_df, board_df)

def page_cbet():
    render_cbet_audit(df_clean, hero_cards_df, board_df)

# Cria o menu de navegação lateral para as outras abas
pg = st.navigation({
    "Painéis Detalhados": [
        st.Page(page_health, title="Saúde Geral", icon="❤️"),
        st.Page(page_overview, title="Visão Geral (Ações)", icon="📊"),
        st.Page(page_villains, title="Mapeamento de Vilões", icon="🕵️‍♂️"),
        st.Page(page_rivalry, title="Ranking de Rivalidade", icon="⚔️"),
        st.Page(page_river, title="Auditoria de River", icon="🌊"),
        st.Page(page_cbet, title="C-Bet e Texturas", icon="🎯"),
    ]
})

# Executa a página selecionada abaixo do Overview
pg.run()