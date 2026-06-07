import streamlit as st
import polars as pl
import json
import os

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

st.set_page_config(layout="wide")

st.title("📊 Poker Telemetry Dashboard (RnC NL2)")

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

st.subheader("Distribuição de Ações")
dist_df = df.group_by("action_type").agg(pl.len())
st.bar_chart(dist_df.to_pandas(), x="action_type", y="len")

st.divider()
st.subheader("🕵️‍♂️ Mapeamento de Vilões e Anotações (Tags)")

df_vencedores = (
    df.filter(pl.col("action_type") == "COLLECT")
    .group_by("hand_id")
    .agg(pl.col("player").unique().alias("lista_vencedores"))
)

df_viloes = (
    df.filter(
        (pl.col("player") != "Hero") & 
        (pl.col("hand_id").str.starts_with("RC"))
    )
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

df_mapeamento = (
    df_viloes.join(df_vencedores, on="hand_id", how="left")
    .join(df_tags, on="player", how="left") 
    .join(df_cartas_viloes, on=["hand_id", "player"], how="left") 
    .join(df_board, on="hand_id", how="left")                     
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

st.write("📝 **Edição Rápida (Dê um duplo clique na célula da coluna 'notas_vilao' para editar)**")
col_sort1, col_sort2 = st.columns([2, 2])

with col_sort1:
    colunas_disponiveis = df_mapeamento.columns
    coluna_ordenacao = st.selectbox(
        "Ordenar tabela pela coluna:",
        options=colunas_disponiveis,
        index=colunas_disponiveis.index("player") if "player" in colunas_disponiveis else 0 
    )
    
with col_sort2:
    ordem_direcao = st.radio(
        "Direção da ordenação:",
        options=["Crescente (A-Z / 0-9)", "Decrescente (Z-A / 9-0)"],
        horizontal=True
    )

is_desc = ordem_direcao.startswith("Decrescente")
df_mapeamento = df_mapeamento.sort(
    coluna_ordenacao, 
    descending=is_desc,
    nulls_last=True
)

pesquisa_vilao = st.text_input("🔍 Buscar Vilão Específico na Tabela:")

if pesquisa_vilao:
    df_mapeamento = df_mapeamento.filter(
        pl.col("player").str.to_lowercase().str.contains(pesquisa_vilao.lower())
    )

edited_df = st.data_editor(
    df_mapeamento.to_pandas(),
    use_container_width=True,
    height=400,
    disabled=["player", "cartas_vilao", "board", "hand_id", "resultado"], 
    key="data_editor_viloes"
)

if st.button("💾 Salvar Todas as Edições no Banco de Tags"):
    tags_atuais = carregar_tags()
    linhas_com_nota = edited_df.dropna(subset=['notas_vilao'])
    
    mudancas = 0
    for _, row in linhas_com_nota.iterrows():
        jogador = row['player']
        nota = str(row['notas_vilao']).strip()
        
        if nota != "" and tags_atuais.get(jogador) != nota:
            tags_atuais[jogador] = nota
            mudancas += 1
            
    if mudancas > 0:
        with open(ARQUIVO_TAGS, "w", encoding="utf-8") as f:
            json.dump(tags_atuais, f, indent=4, ensure_ascii=False)
        st.success(f"✅ {mudancas} anotações atualizadas e sincronizadas!")
        st.rerun() 
    else:
        st.info("Nenhuma alteração nova detectada.")

st.divider()
st.subheader("⚔️ Ranking de Rivalidade (ATMs vs Nemesis)")

df_hero_investido = (
    df.filter(
        (pl.col("player") == "Hero") & 
        (pl.col("action_type").is_in(["SMALL BLIND", "BIG BLIND", "POST", "BET", "CALL", "RAISE"]))
    )
    .group_by("hand_id")
    .agg(pl.col("amount").sum().alias("hero_colocou"))
)

df_hero_ganhou = (
    df.filter((pl.col("player") == "Hero") & (pl.col("action_type") == "COLLECT"))
    .group_by("hand_id")
    .agg(pl.col("amount").sum().alias("hero_puxou"))
)

df_hero_pnl = (
    df.select("hand_id").unique()
    .join(df_hero_investido, on="hand_id", how="left")
    .join(df_hero_ganhou, on="hand_id", how="left")
    .fill_null(0.0) # Proteção contra nulos onde o Hero não agiu
    .with_columns(
        (pl.col("hero_puxou") - pl.col("hero_colocou")).round(2).alias("lucro_liquido_hero")
    )
)

if not df_tags.is_empty():
    df_confrontos = (
        df_viloes.join(df_tags, on="player", how="inner") 
        .join(df_hero_pnl, on="hand_id", how="inner")
        .group_by(["player", "notas_vilao"])
        .agg(
            pl.col("lucro_liquido_hero").sum().round(2).alias("saldo_financeiro"),
            pl.col("hand_id").count().alias("potes_disputados")
        )
        .with_columns(
            pl.when(pl.col("saldo_financeiro") > 0).then(pl.lit("💰 ATM"))
            .when(pl.col("saldo_financeiro") < 0).then(pl.lit("💀 Nemesis"))
            .otherwise(pl.lit("⚖️ Break-even")).alias("classificacao")
        )
    )

    col_atm, col_nemesis = st.columns(2)

    with col_atm:
        st.success("💰 Os seus ATMs (Lucro Máximo Extraído)")
        df_atms = df_confrontos.filter(pl.col("saldo_financeiro") > 0).sort("saldo_financeiro", descending=True)
        st.dataframe(df_atms.to_pandas(), use_container_width=True, hide_index=True)

    with col_nemesis:
        st.error("💀 As suas Nemesis (Vazamento Máximo)")
        df_nems = df_confrontos.filter(pl.col("saldo_financeiro") < 0).sort("saldo_financeiro", descending=False)
        st.dataframe(df_nems.to_pandas(), use_container_width=True, hide_index=True)
        
else:
    st.info("O painel de rivalidade será ativado assim que gravar a primeira anotação num vilão.")