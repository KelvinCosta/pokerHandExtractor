import streamlit as st
import polars as pl
from src.dashboard.data_loader import get_base_dataframe
from src.dashboard.views.sidebar import render_sidebar
from src.dashboard.views.overview import render_overview
from src.dashboard.views.villains import render_villains
from src.dashboard.views.rivalry import render_rivalry
from src.dashboard.views.health import render_health
from src.dashboard.domain_data import get_hero_cards, get_board, get_viloes_cached, get_villains_cards_shown
from src.dashboard.config import carregar_tags
from src.dashboard.views.river_audit import render_river_audit
from src.dashboard.views.cbet_audit import render_cbet_audit
from src.dashboard.views.preflop import render_preflop
from src.dashboard.views.positional import render_positional
from src.dashboard.views.postflop import render_postflop
from src.dashboard.views.population import render_population_range
from src.dashboard.views.big_pots import render_big_pots

st.set_page_config(layout="wide")
st.title("📊 Poker Telemetry Dashboard")

df, nome_coluna_data = get_base_dataframe()
df_clean = render_sidebar(df, nome_coluna_data)

def get_df_tags():
    dicionario_tags = carregar_tags()
    if dicionario_tags:
        return pl.DataFrame({"player": list(dicionario_tags.keys()), "notas_vilao": list(dicionario_tags.values())})
    return pl.DataFrame({"player": [], "notas_vilao": []}, schema={"player": pl.Utf8, "notas_vilao": pl.Utf8})

def page_health():
    render_health(df_clean)

def page_overview():
    render_overview(df_clean)

def page_villains():
    df_viloes = get_viloes_cached(df_clean)
    board_df = get_board(df_clean)
    _ = render_villains(df_clean, df_viloes, board_df)

def page_rivalry():
    df_tags = get_df_tags()
    df_viloes = get_viloes_cached(df_clean)
    render_rivalry(df_clean, df_viloes, df_tags)


def page_river():
    hero_cards_df = get_hero_cards(df_clean)
    board_df = get_board(df_clean)
    render_river_audit(df_clean, hero_cards_df, board_df)

def page_cbet():
    hero_cards_df = get_hero_cards(df_clean)
    board_df = get_board(df_clean)
    render_cbet_audit(df_clean, hero_cards_df, board_df)

def page_preflop():
    render_preflop(df_clean)

def page_positional():
    render_positional(df_clean)


def page_postflop():
    render_postflop(df_clean)


def page_population():
    render_population_range(df_clean)


def page_big_pots():
    hero_cards_df = get_hero_cards(df_clean)
    board_df = get_board(df_clean)
    villains_cards_df = get_villains_cards_shown(df_clean)
    render_big_pots(df_clean, hero_cards_df, board_df, villains_cards_df)


pg = st.navigation({
    "Painéis Detalhados": [
        st.Page(page_health, title="Saúde Geral", icon="❤️"),
        st.Page(page_positional, title="Consciência Posicional", icon="🪑"),
        st.Page(page_preflop, title="Motor Pré-Flop", icon="🔥"),
        st.Page(page_postflop, title="Agressão Pós-Flop", icon="⚔️"),
        st.Page(page_overview, title="Visão Geral (Ações)", icon="📊"),
        st.Page(page_big_pots, title="Auditoria de Potes Grandes", icon="🔥"),
        st.Page(page_villains, title="Mapeamento de Vilões", icon="🕵️‍♂️"),
        st.Page(page_population, title="População e Ranges (MDA)", icon="👥"),
        st.Page(page_rivalry, title="Ranking de Rivalidade", icon="⚔️"),
        st.Page(page_river, title="Auditoria de River", icon="🌊"),
        st.Page(page_cbet, title="C-Bet e Texturas", icon="🎯"),
    ]
})

pg.run()