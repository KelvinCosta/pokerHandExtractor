import streamlit as st
import polars as pl

def render_sidebar(df, nome_coluna_data):
    st.sidebar.header("🔍 Filtros de Análise")
    
    if nome_coluna_data:
        min_date = df.select(pl.col("data_limpa").drop_nulls().min()).item()
        max_date = df.select(pl.col("data_limpa").drop_nulls().max()).item()

        if min_date and max_date:
            filtro_data = st.sidebar.date_input(
                "Selecione o Período das Mãos:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="date_filter"
            )

            if isinstance(filtro_data, tuple) and len(filtro_data) == 2:
                data_inicio, data_fim = filtro_data
                
                df = df.filter(
                    pl.col("data_limpa").is_between(data_inicio, data_fim)
                )
    else:
        st.sidebar.warning("⚠️ Coluna de data não encontrada no seu ficheiro Parquet. Verifique se o nome é 'date' ou 'timestamp'.")
        
    st.sidebar.divider()
    
    # Filtro Dinâmico de Tipo de Jogo
    if "game_type" in df.columns:
        tipos_disponiveis = df.select("game_type").drop_nulls().unique().to_series().to_list()
        
        # Garante que as opções padrão existem nas opções disponíveis (Rush & Cash por padrão)
        default_options = [t for t in tipos_disponiveis if "Rush & Cash" in t]
        if not default_options and tipos_disponiveis:
            default_options = [tipos_disponiveis[0]]
            
        # Inicializar o estado se não existir
        if "game_type_filter" not in st.session_state:
            st.session_state["game_type_filter"] = default_options

        selecionados = st.sidebar.multiselect(
            "🃏 Modalidades de Jogo:",
            options=tipos_disponiveis,
            key="game_type_filter",
            help="Selecione as modalidades que deseja analisar para evitar a mistura de métricas entre torneios e cash games."
        )
        
        if not selecionados:
            st.sidebar.error("Selecione pelo menos um tipo de jogo.")
            st.stop()
            
        df = df.filter(pl.col("game_type").is_in(selecionados))
    else:
        # Backward compatibility (se o banco for antigo e não tiver game_type)
        df = df.filter(pl.col("hand_id").str.starts_with("RC"))
        
    st.sidebar.divider()
    pesquisa_hand_id = st.sidebar.text_input("🔍 Buscar por Hand ID:")
    
    if pesquisa_hand_id:
        df = df.filter(pl.col("hand_id").str.contains(pesquisa_hand_id))
        
        if df.height > 0:
            st.sidebar.markdown("### 📝 Ações da Mão")
            
            if "source_file" in df.columns:
                arquivo_origem = df.select("source_file").head(1).item()
                st.sidebar.caption(f"📂 Origem: `{arquivo_origem}`")

            if "total_pot_final" in df.columns:
                # Pega a primeira linha da mão para extrair o resumo
                resumo = df.head(1)
                tpot = resumo.select("total_pot_final").item()
                rake = resumo.select("rake").item()
                jackpot = resumo.select("jackpot").item()
                bingo = resumo.select("bingo").item()
                
                st.sidebar.info(f"💰 Pote Final: ${tpot:.2f} | 💸 Rake: ${rake:.2f}")
                st.sidebar.info(f"🎰 Jackpot: ${jackpot:.2f} | 🎱 Bingo: ${bingo:.2f}")
                
            # Descobrir a posição na mesa baseada na ordem de ação Pré-Flop
            # A ordem de ação preflop sempre termina no BB. Quem age antes é o SB, antes é BTN, CO, MP, UTG.
            preflop_actions = df.filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") != "POST"))
            
            if preflop_actions.height > 0:
                # Pegar jogadores na ordem exata da primeira ação
                jogadores_ordem = preflop_actions.unique(subset=["player"], maintain_order=True)["player"].to_list()
                
                pos_names = ["BB", "SB", "BTN", "CO", "MP", "UTG", "EP1", "EP2", "EP3"]
                pos_map = {}
                for i, jogador in enumerate(reversed(jogadores_ordem)):
                    if i < len(pos_names):
                        pos_map[jogador] = pos_names[i]
                    else:
                        pos_map[jogador] = "UNK"
                
                # Injeta a posição no df
                df = df.with_columns(
                    pl.col("player").replace_strict(pos_map, default="UNK").alias("position")
                )
            else:
                df = df.with_columns(pl.lit("UNK").alias("position"))

            # Seleciona as colunas relevantes das ações já extraídas do df explodido
            acoes_df = df.select(["street", "position", "player", "action_type", "amount"])
            st.sidebar.dataframe(acoes_df.to_pandas(), hide_index=True, use_container_width=True)
        else:
            st.sidebar.warning("Mão não encontrada no período selecionado.")
        
    df_clean = df.with_columns(
        pl.col("player_cards").list.eval(
            pl.element().struct.field("cards")
        ).list.join(", ").alias("cards_raw")
    )
    
    return df_clean
