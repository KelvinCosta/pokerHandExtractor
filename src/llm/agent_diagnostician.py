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
    gera um laudo determinístico (DiagnosticReport).
    Este agente NÃO fala com o usuário.
    """
    
    # Cálculos determinísticos em Python (Regra de Ouro)
    vpip_delta = abs(stats.behavioral_triggers.recent_trend_vpip - stats.global_stats.vpip)
    pfr_delta = abs(stats.behavioral_triggers.recent_trend_pfr - stats.global_stats.pfr)
    max_delta = max(vpip_delta, pfr_delta)
    
    downswing = stats.behavioral_triggers.max_session_downswing_bb
    
    # 1. Limiares de VPIP/PFR
    if max_delta <= 5.0:
        alerta_stats = "Flutuação Normal (Sem alerta)"
    elif 5.0 < max_delta < 10.0:
        alerta_stats = "Zona Amarela (Alerta de possível quebra de range ou exploração da mesa)"
    else:
        alerta_stats = "Zona Vermelha (Alerta grave de desvio comportamental)"
        
    # 2. Limiares de Downswing (Stop-loss de 300bb)
    if downswing > -150.0:
        alerta_downswing = "Flutuação Padrão (Ignorar)"
    elif -250.0 < downswing <= -150.0:
        alerta_downswing = "Zona de Check-in (Perguntar como está lidando com a variância)"
    else:
        alerta_downswing = "Zona Crítica (Risco iminente de bater o stop-loss)"

    # Usando ChatOllama com structured_output para forçar o retorno Pydantic
    llm = ChatOllama(model="llama3", temperature=0.0)
    structured_llm = llm.with_structured_output(DiagnosticReport)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Você é o Agente 1 (Motor Analítico) de um sistema SaaS B2B de Poker.
Sua única função é compilar um relatório estruturado em JSON baseado estritamente na matemática e nos alertas fornecidos.
NÃO diagnostique "Tilt" nem faça presunções psicológicas com viés emocional. Você deve apenas classificar as anomalias e gerar diretrizes de investigação neutras e baseadas em fatos para o Agente 2.

NÃO FALE COM O USUÁRIO. Retorne ESTRITAMENTE as chaves do contrato de dados Pydantic."""),
        
        ("human", """Emita o laudo para os seguintes dados matemáticos:
VPIP Global: {vpip_global}% | Recente: {vpip_recente}%
PFR Global: {pfr_global}% | Recente: {pfr_recente}%
Sessões Perdendo: {streak}
Downswing Máximo: {downswing} BB
Lucro Acumulado: {profit} BB

=== CONTEXTO DE ALERTA PRÉ-CALCULADO ===
Alerta de Estatísticas (VPIP/PFR): {alerta_stats}
Alerta de Downswing: {alerta_downswing}
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
        "profit": stats.global_stats.profit_bb,
        "alerta_stats": alerta_stats,
        "alerta_downswing": alerta_downswing
    })
    
    return report
