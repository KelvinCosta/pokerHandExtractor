import uuid
from src.api.dependencies import get_current_user
from src.database.models import User
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage

# Dependências locais do LangGraph e esquemas
from src.llm.orchestrator import app as langgraph_app, AuditorState, node_final_reporter
from schemas import PlayerStats
from src.api.schemas.chat import AuditStartRequest, ChatMessageRequest, AuditCompleteRequest

router = APIRouter(prefix="/api/audit", tags=["AI Auditor"])

# Memória temporária para armazenar o estado das conversas do LangGraph.
# No Milestone 2/3, isso será movido para o SQLiteSaver ou Postgres.
ACTIVE_SESSIONS: Dict[str, AuditorState] = {}

@router.post("/start")
def start_audit(request: AuditStartRequest, current_user: User = Depends(get_current_user)):
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

@router.post("/chat")
def send_chat_message(request: ChatMessageRequest, current_user: User = Depends(get_current_user)):
    """
    Recebe uma mensagem do usuário, envia para a sessão ativa do LangGraph
    e retorna a resposta da IA.
    """
    if request.session_id not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
    state = ACTIVE_SESSIONS[request.session_id]
    
    # Adiciona a mensagem do usuário ao histórico
    state["chat_history"].append(HumanMessage(content=request.message))
    
    # Executa apenas o Inquisidor novamente
    from src.llm.orchestrator import inquisitor_node
    
    # Simula a chamada do nó Inquisidor diretamente (já que o grafo pode ser complexo de reentrar no meio)
    # Em produção com LangGraph, usaríamos graph.stream com thread_id
    new_state = inquisitor_node(state)
    
    ACTIVE_SESSIONS[request.session_id] = new_state
    
    ai_response = new_state["chat_history"][-1].content
    return {"response": ai_response}


@router.post("/complete")
def complete_audit(request: AuditCompleteRequest, current_user: User = Depends(get_current_user)):
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
