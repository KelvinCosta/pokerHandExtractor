import streamlit as st
import json
from src.dashboard.config import DATALAKE_SILVER
from src.db.warehouse import DuckDBWarehouse
from src.llm.state_builder import SessionStateCalculator

def render_llm_state(df_clean):
    st.header("🤖 Estado do Jogador (Contexto LLM)")
    st.markdown("Esta tela utiliza a Camada Agnóstica (DuckDB) para acessar a Silver Layer e extrair as métricas comportamentais (Sliding Window) para envio ao modelo de IA.")
    
    col1, col2 = st.columns(2)
    with col1:
        hero_name = st.text_input("Nome do Herói", value="Hero")
    with col2:
        num_hands = st.slider("Janela de Mãos (Sliding Window)", min_value=5, max_value=100, value=20, step=5)
        
    if st.button("Gerar JSON Comportamental"):
        with st.spinner("Consultando camada Silver via DuckDB..."):
            try:
                # O DuckDB lê diretamente do diretório Parquet
                warehouse = DuckDBWarehouse(silver_dir=str(DATALAKE_SILVER))
                calculator = SessionStateCalculator(warehouse)
                
                # Obtem o estado das últimas N mãos
                state = calculator.get_current_state(hero_name=hero_name, num_hands=num_hands)
                
                # Adiciona metadados
                state["context_window_info"] = {
                    "num_hands_analyzed": num_hands,
                    "hero_name": hero_name
                }
                
                st.success("JSON Agrupado e Calculado com Sucesso!")
                st.json(state)
                
            except Exception as e:
                st.error(f"Erro ao consultar dados: {e}")
                st.info("Certifique-se de que a camada Silver (.parquet) já possui dados extraídos.")
