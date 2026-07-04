import uuid
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage

# Dependências locais do LangGraph e esquemas
from src.llm.orchestrator import app as langgraph_app, AuditorState, node_final_reporter
from src.llm.schemas import PlayerStats
from .schemas.chat import AuditStartRequest, ChatMessageRequest, AuditCompleteRequest

router = APIRouter(prefix="/api/audit", tags=["AI Auditor"])

# Memória temporária para armazenar o estado das conversas do LangGraph.
# No Milestone 2/3, isso será movido para o SQLiteSaver ou Postgres.
ACTIVE_SESSIONS: Dict[str, AuditorState] = {}

@router.post("/start")
def start_audit(request: AuditStartRequest):
    """
    Inicia uma nova sessão de auditoria para um jogador específico.
    Aciona o Agente 1 (Motor Analítico) para gerar o laudo inicial
    e o Agente 2 (Inquisidor) para dar a primeira saudação.
    """
    session_id = str(uuid.uuid4())
    
    # TODO: Aqui, você extrairia o PlayerStats real usando o Polars/DuckDB
    # com base nos filtros passados (request.hero_name).
    # Como placeholder para estruturar a API, usaremos dados mockados:
    mock_stats = PlayerStats(
        player_id=request.hero_name,
        vpip=35.0,
        pfr=15.0,
        three_bet=4.0,
        fold_to_3bet=80.0,
        cbet_flop=75.0,
        fold_to_cbet=30.0,
        wtsd=22.0,
        wwsf=40.0,
        bb_100=-5.5,
        total_hands=1500,
        game_type="Rush & Cash"
    )
    
    # Estado inicial do LangGraph
    initial_state = AuditorState(
        player_stats=mock_stats,
        diagnostic_report=None,
        chat_history=[],
        final_report=None
    )
    
    # Executa o grafo: MotorAnalitico -> Inquisidor -> END
    final_state = langgraph_app.invoke(initial_state)
    
    # Salva o estado atual na memória RAM (pelo session_id)
    ACTIVE_SESSIONS[session_id] = final_state
    
    # Extrai a última mensagem (a primeira pergunta do Inquisidor)
    first_ai_message = final_state["chat_history"][-1].content if final_state["chat_history"] else "Olá, vamos começar a auditoria."
    
    return {
        "session_id": session_id,
        "message": first_ai_message,
        "diagnostic_summary": final_state["diagnostic_report"].red_flags if final_state["diagnostic_report"] else []
    }

@router.post("/message")
def chat_message(request: ChatMessageRequest):
    """
    Envia a resposta do jogador para o Inquisidor (Agente 2).
    """
    session_id = request.session_id
    if session_id not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Sessão não encontrada ou expirada.")
        
    state = ACTIVE_SESSIONS[session_id]
    
    # Adiciona a mensagem do usuário ao histórico local
    state["chat_history"].append(HumanMessage(content=request.message))
    
    # Invoca apenas o nó do Inquisidor (já que o MotorAnalítico não precisa rodar de novo)
    from src.llm.orchestrator import node_inquisitor
    new_state = node_inquisitor(state)
    
    # Atualiza o estado
    state["chat_history"] = new_state["chat_history"]
    ACTIVE_SESSIONS[session_id] = state
    
    last_ai_message = state["chat_history"][-1].content
    
    return {
        "session_id": session_id,
        "message": last_ai_message
    }

@router.post("/complete")
def complete_audit(request: AuditCompleteRequest):
    """
    Encerra a conversa e aciona o Agente 3 (Laudo Final) para gerar o relatório comportamental.
    """
    session_id = request.session_id
    if session_id not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Sessão não encontrada ou expirada.")
        
    state = ACTIVE_SESSIONS[session_id]
    
    # Roda o nó final manualmente
    final_state = node_final_reporter(state)
    
    # Limpa a sessão da memória
    del ACTIVE_SESSIONS[session_id]
    
    report = final_state["final_report"]
    return {
        "status": "completed",
        "final_report": report.model_dump() if report else None
    }
