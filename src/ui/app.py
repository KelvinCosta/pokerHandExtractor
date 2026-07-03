import os
import sys
import json
import streamlit as st
from pathlib import Path

# Adiciona a raiz do projeto ao path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from langchain_core.messages import HumanMessage

from src.database.models import init_db, create_audit_session, save_chat_message, complete_audit_session
from src.llm.orchestrator import app as langgraph_app
from src.llm.orchestrator import node_inquisitor, node_final_reporter
from schemas import PlayerStats

# Garante a inicialização do DB
init_db()

st.set_page_config(page_title="SaaS B2B de Poker - Auditoria Comportamental", page_icon="🃏", layout="wide")

# ==========================================
# GESTÃO DE ESTADO
# ==========================================
if "audit_session_id" not in st.session_state:
    st.session_state["audit_session_id"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "langgraph_state" not in st.session_state:
    st.session_state["langgraph_state"] = None
if "final_report" not in st.session_state:
    st.session_state["final_report"] = None

from src.dashboard.config import DATALAKE_SILVER
from src.db.warehouse import DuckDBWarehouse
from src.llm.state_builder import SessionStateCalculator

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("⚙️ Ingestão de Dados")
    
    st.markdown("### 1. Extração DuckDB")
    hero_name = st.text_input("Nome do Herói", value="Hero")
    num_hands = st.slider("Janela de Análise", min_value=5, max_value=100, value=20, step=5)
    
    gerar_duckdb = st.button("🚀 Extrair Estado Atual (DuckDB)")
    
    st.divider()
    st.markdown("### 2. Upload Manual")
    uploaded_file = st.file_uploader("Carregar Histórico (JSON)", type=["json"])
    
    if (gerar_duckdb or uploaded_file is not None) and st.session_state["audit_session_id"] is None:
        try:
            if gerar_duckdb:
                with st.spinner("Consultando Camada Silver no DuckDB..."):
                    warehouse = DuckDBWarehouse(silver_dir=str(DATALAKE_SILVER))
                    calculator = SessionStateCalculator(warehouse)
                    data = calculator.get_current_state(hero_name=hero_name, num_hands=num_hands)
            else:
                data = json.load(uploaded_file)
                
            stats = PlayerStats(**data)
            
            with st.spinner("Motor Analítico a gerar o diagnóstico inicial..."):
                initial_state = {
                    "player_stats": stats,
                    "chat_history": [HumanMessage(content="[SISTEMA]: Inicie a auditoria com o jogador com base no laudo clínico.")]
                }
                
                # Invoca Agente 1 e passa para o Inquisidor
                current_state = langgraph_app.invoke(initial_state)
                st.session_state["langgraph_state"] = current_state
                
                # Regista na Base de Dados
                session_id = create_audit_session(
                    player_id=stats.player_id, 
                    initial_diagnostic=current_state["diagnostic_report"],
                    stats=stats
                )
                st.session_state["audit_session_id"] = session_id
                
                # A primeira pergunta gerada pelo Inquisidor
                first_message = current_state["chat_history"][-1].content
                st.session_state["chat_history"].append({"role": "assistant", "content": first_message})
                save_chat_message(session_id, "assistant", first_message)
                
                st.success("Diagnóstico concluído! Sessão iniciada.")
                st.rerun()
                
        except Exception as e:
            st.error(f"Erro ao processar ficheiro: {e}")

    # Encerramento
    if st.session_state["audit_session_id"] is not None and st.session_state["final_report"] is None:
        st.divider()
        if st.button("🛑 Encerrar Auditoria (Psiquiatra)", use_container_width=True):
            with st.spinner("A avaliar transcrição e a gerar laudo psiquiátrico..."):
                try:
                    final_state = node_final_reporter(st.session_state["langgraph_state"])
                    report = final_state["final_report"]
                    
                    complete_audit_session(st.session_state["audit_session_id"], report)
                    st.session_state["final_report"] = report
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao gerar laudo final: {e}")

# ==========================================
# ÁREA CENTRAL - CHAT SOCRÁTICO
# ==========================================
st.title("🃏 Auditoria Comportamental de Poker")

if st.session_state["final_report"] is not None:
    report = st.session_state["final_report"]
    st.success("A auditoria foi encerrada e o laudo enviado para o gestor da equipa.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Nível de Negação", f"{report.nivel_negacao} / 5")
        st.metric("Admitiu Erro?", "Sim" if report.admitiu_erro else "Não")
    with col2:
        st.subheader("Conclusão Clínica")
        st.write(report.conclusao_entrevista)
        st.subheader("Recomendação do Coach")
        st.write(report.recomendacao_coach)

elif st.session_state["audit_session_id"] is not None:
    # Renderiza histórico
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Input do utilizador
    if user_input := st.chat_input("Justifique a sua decisão..."):
        # 1. Regista e apresenta visualmente (antes de processar para UX fluida)
        st.session_state["chat_history"].append({"role": "user", "content": user_input})
        save_chat_message(st.session_state["audit_session_id"], "user", user_input)
        
        # 2. Atualiza estado e chama o Inquisidor
        st.session_state["langgraph_state"]["chat_history"].append(HumanMessage(content=user_input))
        
        with st.spinner("A analisar a justificação..."):
            try:
                # Invoca diretamente o Inquisidor para manter o contexto rápido
                novo_estado = node_inquisitor(st.session_state["langgraph_state"])
                
                # A nova mensagem
                st.session_state["langgraph_state"]["chat_history"].extend(novo_estado["chat_history"])
                resposta = novo_estado["chat_history"][-1].content
                
                st.session_state["chat_history"].append({"role": "assistant", "content": resposta})
                save_chat_message(st.session_state["audit_session_id"], "assistant", resposta)
                
                st.rerun()
            except Exception as e:
                st.error(f"Ocorreu um erro na análise: {e}")

else:
    st.info("⬅️ Carregue o histórico de mãos (JSON) na barra lateral para iniciar a auditoria.")
