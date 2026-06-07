import streamlit as st
import polars as pl

# Configura o layout como 'wide' para aproveitar a tela
st.set_page_config(layout="wide")

st.title("📊 Poker Telemetry Dashboard (RnC NL2)")

# Carrega os dados uma vez (com cache para o browser não travar)
@st.cache_data
def load_data():
    return pl.scan_parquet("D:/ggpoker/Dados/silver/*.parquet").collect()

df = load_data()

# Filtros laterais (Sidebars)
st.sidebar.header("Filtros")
player_filter = st.sidebar.multiselect("Selecionar Jogador", options=df["player"].unique().to_list())

# Visualização de Tabela Interativa
st.subheader("Auditoria de Mãos")
st.dataframe(df.head(100), use_container_width=True)

# Gráfico simples de distribuição (exemplo)
st.subheader("Distribuição de Ações")
dist_df = df.group_by("action_type").agg(pl.len())
st.bar_chart(dist_df.to_pandas(), x="action_type", y="len")