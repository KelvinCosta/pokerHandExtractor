import streamlit as st
import polars as pl
import datetime
import json
import os

ARQUIVO_TAGS = "tags_viloes.json"

def carregar_tags():
    if not os.path.exists(ARQUIVO_TAGS):
        return {}
    with open(ARQUIVO_TAGS, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_tag(jogador, anotacao):
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

st.sidebar.header("🔍 Filtros de Análise")

nome_coluna_data = "date" if "date" in df.columns else "timestamp" if "timestamp" in df.columns else None

if nome_coluna_data:
    df = df.with_columns(
        pl.col(nome_coluna_data)
        .str.to_datetime("%Y/%m/%d %H:%M:%S", strict=False) # Lê o padrão da GGPoker
        .dt.date() 
        .alias("data_limpa")
    )

    min_date = df.select(pl.col("data_limpa").drop_nulls().min()).item()
    max_date = df.select(pl.col("data_limpa").drop_nulls().max()).item()

    if min_date and max_date:
        filtro_data = st.sidebar.date_input(
            "Selecione o Período das Mãos:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if isinstance(filtro_data, tuple) and len(filtro_data) == 2:
            data_inicio, data_fim = filtro_data
            
            df = df.filter(
                pl.col("data_limpa").is_between(data_inicio, data_fim)
            )
else:
    st.sidebar.warning("⚠️ Coluna de data não encontrada no seu ficheiro Parquet. Verifique se o nome é 'date' ou 'timestamp'.")

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

df_cartas_viloes = (
    df.select(["hand_id", "player_cards"])
    .drop_nulls(subset=["player_cards"])
    .unique(subset=["hand_id"])
    .explode("player_cards")
    .unnest("player_cards") 
    .filter(pl.col("player") != "Hero")
    .select(["hand_id", "player", pl.col("cards").alias("cartas_vilao")])
)

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
    .fill_null(0.0) 
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

hero_cards_df = (
    df
    .select(["hand_id", "player_cards"])
    .drop_nulls(subset=["player_cards"])
    .unique(subset=["hand_id"]) 
    .explode("player_cards")
    .unnest("player_cards")
    .filter(pl.col("player") == "Hero")
    .select(["hand_id", pl.col("cards").alias("hero_cards")])
)

board_df = (
    df
    .select(["hand_id", "board_cards"])
    .drop_nulls(subset=["board_cards"])
    .unique(subset=["hand_id"])
    .with_columns(
        pl.col("board_cards").list.unique(maintain_order=True).list.join(" ").alias("board")
    )
    .select(["hand_id", "board"])
)

vencedores_df = (
    df
    .filter(pl.col("action_type") == "COLLECT")
    .group_by("hand_id")
    .agg(pl.col("player").alias("lista_vencedores"))
    .with_columns(
        pl.col("lista_vencedores").list.contains("Hero").fill_null(False).alias("hero_ganhou")
    )
)

auditoria_base = (
    df
    .filter(
        (pl.col("hand_id").str.starts_with("RC")) & 
        (pl.col("street") == "RIVER")
    )
    .group_by("hand_id")
    .agg(
        pl.col("current_pot").first().alias("pote_final"),
        pl.col("amount").filter(pl.col("action_type").is_in(["BET", "CALL", "RAISE"])).sum().alias("investimento_total_river"),
        pl.col("amount").filter((pl.col("player") == "Hero") & (pl.col("action_type") == "BET")).sum().alias("hero_bet_amount"),
        pl.col("player").filter((pl.col("player") != "Hero") & (pl.col("action_type") == "CALL")).count().alias("qtd_calls_recebidos")
    )
    .filter((pl.col("hero_bet_amount") > 0) & (pl.col("qtd_calls_recebidos") > 0))
    .with_columns((pl.col("pote_final") - pl.col("investimento_total_river")).alias("pote_anterior"))
    .with_columns(((pl.col("hero_bet_amount") / pl.col("pote_anterior")) * 100).round(1).alias("sizing_pct"))
)

auditoria_final = (
    auditoria_base
    .join(hero_cards_df, on="hand_id", how="left")
    .join(board_df, on="hand_id", how="left")
    .join(vencedores_df, on="hand_id", how="left")
    .with_columns(
        pl.when(pl.col("hero_ganhou") == True).then(pl.lit("✅ GANHOU")).otherwise(pl.lit("❌ PERDEU")).alias("resultado")
    )
    .select([
        "hand_id", "pote_anterior", "hero_bet_amount", "sizing_pct", "hero_cards", "board", "resultado"
    ])
    .sort("sizing_pct", descending=False)
)

auditoria_ev = (
    auditoria_final
    .with_columns(
        (pl.col("pote_anterior") * 0.75).round(2).alias("bet_ideal_75")
    )
    .with_columns(
        (pl.col("bet_ideal_75") - pl.col("hero_bet_amount")).round(2).alias("diferenca_dolares")
    )
    .with_columns(
        
        pl.when((pl.col("resultado") == "✅ GANHOU") & (pl.col("diferenca_dolares") > 0))
        .then(pl.lit("💸 Deixou de ganhar: $") + pl.col("diferenca_dolares").cast(pl.Utf8))
        
        .when((pl.col("resultado") == "❌ PERDEU") & (pl.col("diferenca_dolares") > 0))
        .then(pl.lit("🛡️ Sorte (Poupou): $") + pl.col("diferenca_dolares").cast(pl.Utf8))
        
        .when((pl.col("resultado") == "✅ GANHOU") & (pl.col("diferenca_dolares") < 0))
        .then(pl.lit("🔥 Extração Máxima (Overbet)"))
        
        .when((pl.col("resultado") == "❌ PERDEU") & (pl.col("diferenca_dolares") < 0))
        .then(pl.lit("🩸 Desperdício: $") + (pl.col("diferenca_dolares") * -1).cast(pl.Utf8))
        
        .otherwise(pl.lit("⚖️ Na Medida"))
        .alias("impacto_no_caixa")
    )
)


st.dataframe(auditoria_ev, use_container_width=True, hide_index=True)

lucro_perdido = auditoria_ev.filter(
    (pl.col("resultado") == "✅ GANHOU") & (pl.col("diferenca_dolares") > 0)
)["diferenca_dolares"].sum()

dinheiro_salvo = auditoria_ev.filter(
    (pl.col("resultado") == "❌ PERDEU") & (pl.col("diferenca_dolares") > 0)
)["diferenca_dolares"].sum()

balanco_real = lucro_perdido - dinheiro_salvo

st.divider()
st.subheader("💰 Resumo do Caixa do Sprint Atual")
st.caption("Aviso: Pressupõe stacks infinitos e que o vilão daria Call nos 75%.")

col1, col2, col3 = st.columns(3)
col1.metric("💸 Lucro Perdido", f"${lucro_perdido:.2f}")
col2.metric("🛡️ Dinheiro Salvo", f"${dinheiro_salvo:.2f}")
col3.metric("📉 Balanço de Vazamento", f"${balanco_real:.2f}", delta="- Vazamento", delta_color="inverse")