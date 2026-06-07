import streamlit as st
import polars as pl
import json
import os

# =====================================================================
# CAMADA DE PERSISTÊNCIA (dim_tags)
# =====================================================================
ARQUIVO_TAGS = "tags_viloes.json"

def carregar_tags():
    """Lê o arquivo JSON. Se não existir, retorna um dicionário vazio."""
    if not os.path.exists(ARQUIVO_TAGS):
        return {}
    with open(ARQUIVO_TAGS, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_tag(jogador, anotacao):
    """Atualiza o dicionário e sobrescreve o arquivo JSON de forma segura."""
    tags = carregar_tags()
    tags[jogador] = anotacao
    with open(ARQUIVO_TAGS, "w", encoding="utf-8") as f:
        json.dump(tags, f, indent=4, ensure_ascii=False)

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
# MÓDULO DE IDENTIFICAÇÃO DE VILÕES (Engenharia Reversa de Identidade)
# =====================================================================
st.divider()
st.subheader("🕵️‍♂️ Mapeamento de Vilões e Anotações (Tags)")

df_vencedores = (
    df.filter(pl.col("action_type") == "COLLECT")
    .group_by("hand_id")
    .agg(pl.col("player").unique().alias("lista_vencedores"))
)

df_viloes = (
    df.filter(pl.col("player") != "Hero")
    .select(["hand_id", "player"])
    .unique() 
)

# NOVO: Extrai as cartas exatas que o vilão mostrou no Showdown
df_cartas_viloes = (
    df.select(["hand_id", "player_cards"])
    .drop_nulls(subset=["player_cards"])
    .unique(subset=["hand_id"])
    .explode("player_cards")
    .unnest("player_cards") # Separa o dicionário em colunas 'player' e 'cards'
    .filter(pl.col("player") != "Hero")
    .select(["hand_id", "player", pl.col("cards").alias("cartas_vilao")])
)

# NOVO: Extrai o Bordo da mão para facilitar a busca no PokerCraft
df_board = (
    df.select(["hand_id", "board_cards"])
    .drop_nulls(subset=["board_cards"])
    .unique(subset=["hand_id"])
    .with_columns(
        pl.col("board_cards").list.unique(maintain_order=True).list.join(" ").alias("board")
    )
    .select(["hand_id", "board"])
)

dicionario_tags = carregar_tags()

if dicionario_tags:
    df_tags = pl.DataFrame(
        {"player": list(dicionario_tags.keys()), "notas_vilao": list(dicionario_tags.values())}
    )
else:
    df_tags = pl.DataFrame({"player": [], "notas_vilao": []}, schema={"player": pl.Utf8, "notas_vilao": pl.Utf8})

# O JOIN Mestre atualizado com o Contexto Visual
df_mapeamento = (
    df_viloes.join(df_vencedores, on="hand_id", how="left")
    .join(df_tags, on="player", how="left") 
    .join(df_cartas_viloes, on=["hand_id", "player"], how="left") # Injeta as cartas
    .join(df_board, on="hand_id", how="left")                     # Injeta o board
    .with_columns(
        pl.col("lista_vencedores").list.contains(pl.col("player")).fill_null(False).alias("vilao_ganhou")
    )
    .with_columns(
        pl.when(pl.col("vilao_ganhou") == True).then(pl.lit("✅ GANHOU"))
        .otherwise(pl.lit("❌ PERDEU")).alias("resultado")
    )
    # Ordem cirúrgica das colunas para facilitar a leitura humana
    .select(["player", "notas_vilao", "cartas_vilao", "board", "hand_id", "resultado"])
    .sort(["player", "hand_id"])
)

# =====================================================================
# INTERFACE DE USUÁRIO (Formulário e Tabela)
# =====================================================================

# Usamos st.form para evitar que a tela pisque a cada letra digitada
with st.form("form_anotacao"):
    st.write("✍️ **Adicionar ou Editar Perfil do Vilão**")
    col_input1, col_input2, col_input3 = st.columns([2, 4, 1])
    
    with col_input1:
        input_nome = st.text_input("Nome exato (ex: AlienPoker99):")
    with col_input2:
        input_tag = st.text_input("Anotação (ex: Fish - Paga tudo no River):")
    with col_input3:
        st.write("") # Espaçamento
        st.write("") # Espaçamento
        submit_tag = st.form_submit_button("💾 Salvar")
        
    if submit_tag and input_nome:
        salvar_tag(input_nome, input_tag)
        st.success(f"Tag de '{input_nome}' salva com sucesso!")
        st.rerun() # Reinicia a aplicação para a tabela puxar os dados atualizados

# Pesquisa e Tabela
pesquisa_vilao = st.text_input("🔍 Buscar Vilão Específico na Tabela:")

if pesquisa_vilao:
    df_mapeamento = df_mapeamento.filter(
        pl.col("player").str.to_lowercase().str.contains(pesquisa_vilao.lower())
    )

# =====================================================================
# CONTROLO DE ORDENAÇÃO EXPLÍCITO (Gestão de Estado no Backend)
# =====================================================================
st.write("🔀 **Controlo de Visualização**")
col_sort1, col_sort2 = st.columns([2, 2])

with col_sort1:
    # Extrai a lista de colunas disponíveis dinamicamente
    colunas_disponiveis = df_mapeamento.columns
    coluna_ordenacao = st.selectbox(
        "Ordenar tabela pela coluna:",
        options=colunas_disponiveis,
        # Define o 'player' como padrão
        index=colunas_disponiveis.index("player") if "player" in colunas_disponiveis else 0 
    )
    
with col_sort2:
    ordem_direcao = st.radio(
        "Direção da ordenação:",
        options=["Crescente (A-Z / 0-9)", "Decrescente (Z-A / 9-0)"],
        horizontal=True
    )

# Aplica a ordenação no motor Rust (Polars) antes de renderizar
is_desc = ordem_direcao.startswith("Decrescente")
df_mapeamento = df_mapeamento.sort(coluna_ordenacao, descending=is_desc)

# Renderiza a tabela já processada e estruturada
st.dataframe(df_mapeamento, use_container_width=True, height=400)