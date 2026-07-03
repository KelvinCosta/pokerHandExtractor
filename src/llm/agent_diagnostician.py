import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from schemas import PlayerStats, DiagnosticReport

def run_diagnostician(stats: PlayerStats) -> DiagnosticReport:
    """
    Agente 1 (Motor Matemático): Analisa os dados frios (PlayerStats) e 
    gera um laudo clínico determinístico (DiagnosticReport).
    Este agente NÃO fala com o usuário.
    """
    # Usando ChatOllama com structured_output para forçar o retorno Pydantic
    llm = ChatOllama(model="llama3", temperature=0.0)
    structured_llm = llm.with_structured_output(DiagnosticReport)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Você é o Agente 1 (Motor Analítico) de um sistema SaaS B2B de Poker.
Sua única função é ler os dados matemáticos do jogador e emitir um laudo comportamental estruturado.

HEURÍSTICAS OBRIGATÓRIAS:
- Se VPIP subiu consideravelmente (> 3%) atrelado a um Downswing Severo (< -100bb): Diagnostique como 'Tilt de Raiva' ou 'Monkey Tilt' (Gravidade 4 ou 5). A diretriz deve orientar o Agente 2 a pressionar o jogador sobre o abandono de disciplina pré-flop após o tombo.
- Se há Sequência de Derrotas (Streak >= 2): Diagnostique como 'Medo de Perder' (Gravidade 3 ou 4). A diretriz deve orientar o Agente 2 a investigar se o jogador está hesitando e jogando passivo.
- Se os deltas são baixos e lucro positivo: Diagnostique como 'Sólido' (Gravidade 1 ou 2).

NÃO HALE COM O USUÁRIO. Retorne ESTRITAMENTE as chaves do contrato de dados Pydantic."""),
        
        ("human", """Emita o laudo para os seguintes dados:
VPIP Global: {vpip_global}% | Recente: {vpip_recente}%
PFR Global: {pfr_global}% | Recente: {pfr_recente}%
Sessões Perdendo: {streak}
Downswing Máximo: {downswing} BB
Lucro Acumulado: {profit} BB
""")
    ])
    
    chain = prompt | structured_llm
    
    print("🧠 [Agente 1] Analisando métricas matemáticas e extraindo laudo clínico...")
    report = chain.invoke({
        "vpip_global": stats.global_stats.vpip,
        "vpip_recente": stats.behavioral_triggers.recent_trend_vpip,
        "pfr_global": stats.global_stats.pfr,
        "pfr_recente": stats.behavioral_triggers.recent_trend_pfr,
        "streak": stats.behavioral_triggers.current_losing_streak_sessions,
        "downswing": stats.behavioral_triggers.max_session_downswing_bb,
        "profit": stats.global_stats.profit_bb
    })
    
    return report
