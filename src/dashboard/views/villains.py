import streamlit as st
import polars as pl
from ..config import carregar_tags, salvar_tag, ARQUIVO_TAGS
import json

def get_df_viloes(df):
    return (
        df.filter(
            (pl.col("player") != "Hero") & 
            (pl.col("hand_id").str.starts_with("RC"))
        )
        .select(["hand_id", "player"])
        .unique() 
    )

def render_villains(df, df_viloes, df_board):
    st.divider()
    st.subheader("🕵️‍♂️ Mapeamento de Vilões e Anotações (Tags)")

    df_vencedores = (
        df.filter(pl.col("action_type") == "COLLECT")
        .group_by("hand_id")
        .agg(pl.col("player").unique().alias("lista_vencedores"))
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
    
    return df_tags
