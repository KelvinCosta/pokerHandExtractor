import streamlit as st
import polars as pl

# Configura o layout como 'wide' para aproveitar a tela
st.set_page_config(layout="wide")

st.title("📊 Poker Telemetry Dashboard (RnC NL2)")

# Carrega os dados uma vez (com cache para o browser não travar)
@st.cache_data
def load_data():
    df = pl.scan_parquet("D:/ggpoker/Dados/silver/*.parquet").collect()
    df_gold = df.explode("actions").unnest("actions")
    return df_gold

df = load_data()
df_clean = df.with_columns(
    pl.col("player_cards").list.eval(
        pl.element().struct.field("cards")
    ).list.join(", ").alias("cards_raw")
)

# Filtros laterais (Sidebars)
st.sidebar.header("Filtros")
player_list = df_clean["player"].unique().drop_nulls().to_list()
player_filter = st.sidebar.multiselect("Selecionar Jogador", options=df_clean["player"].unique().to_list())

# Visualização de Tabela Interativa
st.subheader("Auditoria de Mãos")
df_viz = df.clone()
df_viz = df.with_columns(
        pl.col("player_cards").list.eval(
            pl.element().struct.field("player") + pl.lit(": ") + pl.element().struct.field("cards")
        ).list.join(" | ").alias("cartas_distribuidas")
    )
colunas_ordenadas = [
        "hand_id", 
        "player", 
        "action_type", 
        "amount", 
        "street",
        "cartas_distribuidas", 
        "board_cards"
    ]
df_viz = df_viz.select(colunas_ordenadas)
st.dataframe(df_viz, use_container_width=True)

# Gráfico simples de distribuição (exemplo)
st.subheader("Distribuição de Ações")
dist_df = df.group_by("action_type").agg(pl.len())
st.bar_chart(dist_df.to_pandas(), x="action_type", y="len")

# =====================================================================
# MÓDULO DE IDENTIFICAÇÃO DE VILÕES (O "Trabalho de Formiguinha")
# =====================================================================
st.divider() 
st.subheader("🕵️‍♂️ Mapeamento de Vilões")

# 1. Tabela de Vencedores (Quem puxou o pote na mão?)
df_vencedores = (
    df.filter(pl.col("action_type") == "COLLECT")
    .group_by("hand_id")
    .agg(pl.col("player").unique().alias("lista_vencedores"))
)

# 2. Tabela de Vilões por Mão (Remove o Hero e extrai participantes únicos)
df_viloes = (
    df.filter(pl.col("player") != "Hero")
    .select(["hand_id", "player"])
    .unique() # Garante que o vilão só apareça 1 vez por hand_id
)

# 3. O JOIN Mestre (Avalia o resultado individual de cada vilão)
df_mapeamento = (
    df_viloes.join(df_vencedores, on="hand_id", how="left")
    .with_columns(
        # Verifica se o nome do vilão está dentro da lista de quem deu COLLECT
        pl.col("lista_vencedores").list.contains(pl.col("player"))
        .fill_null(False)
        .alias("vilao_ganhou")
    )
    .with_columns(
        pl.when(pl.col("vilao_ganhou") == True)
        .then(pl.lit("✅ GANHOU"))
        .otherwise(pl.lit("❌ PERDEU"))
        .alias("resultado")
    )
    # Limpa as colunas temporárias e ordena ALFABETICAMENTE pelo nome do vilão
    .select(["player", "hand_id", "resultado"])
    .sort(["player", "hand_id"]) 
)

# 4. Interface de Pesquisa Ativa
col1, col2 = st.columns([1, 3])
with col1:
    # Permite que você digite parte do nome para achar o vilão rapidamente
    pesquisa_vilao = st.text_input("🔍 Buscar Vilão Específico:")

if pesquisa_vilao:
    # Filtro case-insensitive (ignora maiúsculas/minúsculas)
    df_mapeamento = df_mapeamento.filter(
        pl.col("player").str.to_lowercase().str.contains(pesquisa_vilao.lower())
    )

with col2:
    st.dataframe(df_mapeamento, use_container_width=True, height=400)