import os
import sys
import json
from pathlib import Path
from typing import TypedDict, Annotated, Optional
import operator

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama

from schemas import PlayerStats, DiagnosticReport, FinalBehavioralReport
from src.llm.agent_diagnostician import run_diagnostician

# ==========================================
# 1. ESTADO DA MÁQUINA DE ESTADOS (LANGGRAPH)
# ==========================================
class AuditorState(TypedDict):
    player_stats: PlayerStats
    diagnostic_report: Optional[DiagnosticReport]
    chat_history: Annotated[list[BaseMessage], operator.add] # Operator.add junta a lista
    final_report: Optional[FinalBehavioralReport]

# ==========================================
# 2. NÓS DO GRAFO (AGENTES)
# ==========================================
def node_diagnostician(state: AuditorState):
    """Agente 1: Analisa dados e gera relatório estruturado."""
    report = run_diagnostician(state["player_stats"])
    
    # Persiste o laudo de diagnóstico no disco para auditoria da plataforma B2B
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    player_id = state["player_stats"].player_id
    audit_path = root_dir / f"diagnostic_{player_id}_{timestamp}.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=4))
    print(f"💾 Laudo inicial (Motor Analítico) salvo em: {audit_path}")
        
    return {"diagnostic_report": report}

def node_inquisitor(state: AuditorState):
    """Agente 2: Conversa com o usuário usando o laudo do Agente 1."""
    report = state["diagnostic_report"]
    history = state["chat_history"]
    
    llm = ChatOllama(model="llama3", temperature=0.7)
    
    system_prompt = f"""Você é o Agente de Sondagem (Psicólogo Esportivo) de um sistema SaaS B2B de Poker.
Seu papel é conversar com o jogador sobre as anomalias detectadas. Seja extremamente educado, compreensivo e acolhedor.
PROIBIDO julgar, brigar ou chamar o jogador de mentiroso. Se ele der uma desculpa (ex: azar, variância, desconhecimento), valide o sentimento dele, mas faça uma nova pergunta sutil para aprofundar o tema.

=== RELATÓRIO DE ANOMALIAS ===
Status: {report.status_variancia} (Gravidade: {report.nivel_gravidade}/5)
Bandeiras: {', '.join(report.red_flags)}

=== INSTRUÇÕES ===
1. Aja como um terapeuta. Deixe o jogador confortável para falar o que quiser.
2. Faça perguntas curtas e reflexivas.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"history": history})
    
    return {"chat_history": [response]}

def node_final_reporter(state: AuditorState):
    """Gera o laudo estruturado final ao encerramento do chat."""
    llm = ChatOllama(model="llama3", temperature=0.0).with_structured_output(FinalBehavioralReport)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Você é o Psiquiatra Clínico Sênior auditando uma transcrição de terapia. 
    Sua função é avaliar o comportamento do paciente (jogador) e preencher o laudo JSON com precisão cirúrgica e frieza.
    
    REGRA CRÍTICA PARA 'NÍVEL DE NEGAÇÃO' (1-5):
    - Nível 1: O jogador assume total responsabilidade técnica e emocional pelos números ruins.
    - Nível 3: O jogador tenta dividir a culpa (assume um pouco, mas culpa a variância/baralho).
    - Nível 5: O jogador age com vitimismo agressivo, culpa exclusivamente o "azar", finge ignorância sobre estatísticas básicas (ex: não saber o que é VPIP ou BB) ou dá respostas irônicas.
    
    REGRA CRÍTICA PARA 'ADMITIU ERRO':
    - Só deve ser `True` se o jogador disser explicitamente que jogou mal ou que se descontrolou. Evasão ou culpar o azar DEVE resultar em `False`.
    
    Seja implacável na sua 'conclusao_entrevista'. Se o jogador se fez de desentendido ou culpou a sorte, aponte isso como uma RED FLAG psicológica grave."""),
        MessagesPlaceholder(variable_name="history")
    ])
    
    chain = prompt | llm
    print("\n🧠 [Agente 2] Consolidando histórico e emitindo laudo comportamental...")
    report = chain.invoke({"history": state["chat_history"]})
    
    # Persiste o laudo final no disco para auditoria da plataforma B2B
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    player_id = state["player_stats"].player_id
    audit_path = root_dir / f"final_report_{player_id}_{timestamp}.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=4))
    print(f"💾 Laudo final comportamental salvo em: {audit_path}")
        
    return {"final_report": report}

# ==========================================
# 3. CONSTRUÇÃO DO GRAFO
# ==========================================
workflow = StateGraph(AuditorState)

workflow.add_node("MotorAnalitico", node_diagnostician)
workflow.add_node("Inquisidor", node_inquisitor)
workflow.add_node("LaudoFinal", node_final_reporter)

# O fluxo sempre inicia no Agente 1, que passa a bola pro Agente 2.
workflow.set_entry_point("MotorAnalitico")
workflow.add_edge("MotorAnalitico", "Inquisidor")

# Na arquitetura interativa CLI, o Inquisidor devolve o controle para o humano rodando num loop externo.
# Por isso o Grafo interrompe após o Inquisidor (através do END ou de um Breakpoint) 
# para pegar a mensagem do usuário. 
workflow.add_edge("Inquisidor", END) 
workflow.add_edge("LaudoFinal", END)

# Compila o Grafo
app = workflow.compile()

# ==========================================
# 4. ORQUESTRAÇÃO DE TERMINAL (LOOP)
# ==========================================
if __name__ == "__main__":
    json_path = root_dir / "current_state.json"
    if not json_path.exists():
        print("Erro: current_state.json não encontrado.")
        sys.exit(1)
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    stats = PlayerStats(**data)
    
    # 1. Rodar até o Agente 1 entregar e o Agente 2 dar a primeira saudação
    print("🚀 Iniciando Arquitetura Multi-Agente (LangGraph)...")
    
    # Inicia o estado com uma mensagem fictícia para acionar o LLM
    initial_state = {
        "player_stats": stats,
        "chat_history": [HumanMessage(content="[SISTEMA]: Inicie a auditoria com o jogador com base no laudo clínico.")]
    }
    
    # Executa os nós 'MotorAnalitico' -> 'Inquisidor'
    current_state = app.invoke(initial_state)
    
    print("\n=== 🔮 AUDITOR (Agente 2) ===")
    print(current_state["chat_history"][-1].content)
    print("=================================\n")
    
    # 2. Loop Interativo Humano
    while True:
        try:
            resposta_jogador = input("🗣️  Sua resposta (ou 'sair' para encerrar): ")
            
            if resposta_jogador.lower() in ['sair', 'exit', 'quit']:
                print("\n[SISTEMA]: Encerrando chat. Acionando Nó de Laudo Final...")
                
                # Executa o Nó de fechamento manualmente com o estado atualizado
                final_state = node_final_reporter(current_state)
                report = final_state["final_report"]
                
                print("\n=== 📄 LAUDO COMPORTAMENTAL FINAL ===")
                print(f"Admitiu erro? {report.admitiu_erro}")
                print(f"Nível de Negação (1-5): {report.nivel_negacao}")
                print(f"Conclusão da Entrevista: {report.conclusao_entrevista}")
                print(f"Recomendação de Coach: {report.recomendacao_coach}")
                print("=====================================")
                break
            
            # Adiciona a resposta do Humano ao estado e invoca SOMENTE o Inquisidor
            current_state["chat_history"].append(HumanMessage(content=resposta_jogador))
            
            # Invocamos diretamente o node_inquisitor para manter velocidade
            # pois não precisamos que o Agente 1 rode de novo.
            novo_estado = node_inquisitor(current_state)
            current_state["chat_history"].extend(novo_estado["chat_history"])
            
            print("\n=== 🔮 AUDITOR (Agente 2) ===")
            print(current_state["chat_history"][-1].content)
            print("=================================\n")
            
        except KeyboardInterrupt:
            print("\n\n[SISTEMA]: Interrompido pelo usuário.")
            break
