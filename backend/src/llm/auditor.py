import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar schemas.py sem quebrar o módulo
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from schemas import PlayerStats

def build_auditor_prompt(stats: PlayerStats) -> ChatPromptTemplate:
    """
    Compila o System Prompt dinâmico para o Agente LangChain com base nas estatísticas imutáveis.
    Respeita Clean Architecture isolando a formatação do LLM da extração (DuckDB) e da execução.
    """
    # 1. Calcular deltas matemáticos em Python
    vpip_delta = stats.behavioral_triggers.recent_trend_vpip - stats.global_stats.vpip
    pfr_delta = stats.behavioral_triggers.recent_trend_pfr - stats.global_stats.pfr
    
    # 2. Resgatar Gatilhos do Pydantic
    downswing = stats.behavioral_triggers.max_session_downswing_bb
    streak = stats.behavioral_triggers.current_losing_streak_sessions
    
    # 3. Calibrar Abordagem (Diretriz Dinâmica)
    approach_directive = ""
    
    # Heurística: VPIP alto + Tombo grande = Macaco Tilt
    if vpip_delta >= 3.0 and downswing <= -100.0:
        approach_directive = (
            "O jogador sofreu um downswing severo recentemente e afrouxou muito seu range (VPIP subiu). "
            "Há forte probabilidade de perda de paciência (Tilt). Inicie a conversa questionando incisivamente "
            "o processamento mental e a qualidade da tomada de decisão durante essa queda específica."
        )
    # Heurística: Streak negativa = Falta de Confiança / Medo
    elif streak >= 2:
        approach_directive = (
            f"O jogador está amargando uma sequência de {streak} sessões consecutivas no vermelho. "
            "Questione de forma socrática e direta como essa sequência está afetando a confiança e se "
            "ele está jogando com medo de perder mais."
        )
    # Heurística base
    else:
        approach_directive = (
            "O jogador não apresenta gatilhos severos de tilt de curto prazo no momento. "
            "Conduza a auditoria questionando de forma socrática se ele está satisfeito com "
            "sua taxa de vitória atual e se percebe algum padrão invisível vazando lucros."
        )

    # 4. Construir o Template do Sistema (Regras Duras)
    system_template = f"""
    [DIRETRIZ DO SISTEMA]
    Você é um Auditor Comportamental de Poker (SaaS B2B).
    SUA REGRA PRIMÁRIA: VOCÊ NÃO ENSINA A JOGAR POKER. Proibido dar dicas técnicas, estratégicas, falar sobre teoria de poker ou corrigir ranges.
    Sua única função é diagnosticar desvios psicológicos e risco de tilt comparando as métricas base (histórico) com os gatilhos recentes.

    Adote uma postura SOCRÁTICA, SECA e OBJETIVA:
    - Faça perguntas curtas e incisivas.
    - Force o jogador a justificar seu estado mental e escolhas sob pressão.
    - NUNCA use analogias. Não seja empático.

    === CONTEXTO DO JOGADOR ===
    VPIP Global: {stats.global_stats.vpip:.2f}% | VPIP Recente: {stats.behavioral_triggers.recent_trend_vpip:.2f}% (Delta: {vpip_delta:+.2f}%)
    PFR Global: {stats.global_stats.pfr:.2f}% | PFR Recente: {stats.behavioral_triggers.recent_trend_pfr:.2f}% (Delta: {pfr_delta:+.2f}%)
    Lucro Total Acumulado: {stats.global_stats.profit_bb} BB
    Sessões Consecutivas Perdendo (Streak): {streak}
    Maior Queda em Única Sessão (Downswing): {downswing} BB

    === DIRETRIZ DE ABORDAGEM CALIBRADA (Siga rigorosamente para iniciar) ===
    {approach_directive}
    """

    # 5. Retorna o template pronto e puro do LangChain
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_template),
        HumanMessagePromptTemplate.from_template("{user_input}")
    ])
    
    return prompt

if __name__ == "__main__":
    import json
    
    # Carrega o JSON gerado pelo DuckDB
    json_path = root_dir / "current_state.json"
    if not json_path.exists():
        print("Erro: current_state.json não encontrado. Rode o bridge_duckdb.py primeiro.")
        sys.exit(1)
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Inicializa o contrato imutável
    stats = PlayerStats(**data)
    
    # Compila o prompt
    prompt = build_auditor_prompt(stats)
    
    # Exibe no terminal para debug
    print("=== PROMPT DO SISTEMA COMPILADO ===")
    print(prompt.messages[0].prompt.template)
    print("===================================")