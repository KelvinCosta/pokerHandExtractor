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
                max_value=max_date
            )

            if isinstance(filtro_data, tuple) and len(filtro_data) == 2:
                data_inicio, data_fim = filtro_data
                
                df = df.filter(
                    pl.col("data_limpa").is_between(data_inicio, data_fim) &
                    pl.col("hand_id").str.starts_with("RC")
                )
    else:
        st.sidebar.warning("⚠️ Coluna de data não encontrada no seu ficheiro Parquet. Verifique se o nome é 'date' ou 'timestamp'.")
        
    st.sidebar.divider()
    pesquisa_hand_id = st.sidebar.text_input("🔍 Buscar por Hand ID:")
    
    if pesquisa_hand_id:
        df = df.filter(pl.col("hand_id").str.contains(pesquisa_hand_id))
        
        if df.height > 0:
            st.sidebar.markdown("### 📝 Ações da Mão")
            
            if "source_file" in df.columns:
                arquivo_origem = df.select("source_file").head(1).item()
                st.sidebar.caption(f"📂 Origem: `{arquivo_origem}`")
                
            # Seleciona as colunas relevantes das ações já extraídas do df explodido
            acoes_df = df.select(["street", "player", "action_type", "amount"])
            st.sidebar.dataframe(acoes_df.to_pandas(), hide_index=True, use_container_width=True)
        else:
            st.sidebar.warning("Mão não encontrada no período selecionado.")
        
    df_clean = df.with_columns(
        pl.col("player_cards").list.eval(
            pl.element().struct.field("cards")
        ).list.join(", ").alias("cards_raw")
    )
    
    return df_clean
