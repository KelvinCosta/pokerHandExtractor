from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class TimeWindow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    start_date: datetime = Field(..., description="Início da janela de tempo analisada")
    end_date: datetime = Field(..., description="Fim da janela de tempo analisada")
    stake_level: float = Field(..., description="Nível de aposta (ex: 2.0 para NL2, 10.0 para NL10)")

class GlobalStats(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    hands_played: int = Field(0, description="Volume total de mãos")
    win_rate_bb100: float = Field(0.0, description="Lucro em BBs por 100 mãos")
    ev_bb100: float = Field(0.0, description="EV All-In em BBs por 100 mãos")
    ev_diff_bb: float = Field(0.0, description="Diferença entre Sorte e EV (bb)")
    profit_bb: float = Field(..., description="Lucro total (BB)")
    vpip: float = Field(0.0, description="Voluntarily Put Money in Pot (%)")
    pfr: float = Field(0.0, description="Pre-Flop Raise (%)")
    aggressiveness_factor: float = Field(..., description="Fator de agressividade (AF)")
    all_in_freq: float = Field(0.0, description="Frequência de All-In (%)")
    wsd: float = Field(0.0, description="Won Money at Showdown (W$SD %)")
    wwsf: float = Field(0.0, description="Won When Saw Flop (WWSF %)")

class BehavioralTriggers(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    recent_trend_vpip: float = Field(..., description="VPIP nas mãos recentes (últimos 25%)")
    recent_trend_pfr: float = Field(..., description="PFR nas mãos recentes (últimos 25%)")
    recent_profit_bb: float = Field(..., description="Lucro nas mãos recentes (últimos 25%)")
    recent_aggressiveness_factor: float = Field(..., description="Fator de agressividade nas mãos recentes (últimos 25%)")
    current_losing_streak_sessions: int = Field(..., description="Sessões/Dias consecutivos no vermelho até hoje")
    max_session_downswing_bb: float = Field(..., description="Maior queda em uma única sessão/dia (BB)")

class PlayerStats(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    player_id: str = Field(..., description="Identificador único do jogador")
    time_window: TimeWindow = Field(..., description="Metadados da janela de tempo")
    global_stats: GlobalStats = Field(..., description="Estatísticas gerais de performance (Longo Prazo)")
    behavioral_triggers: BehavioralTriggers = Field(..., description="Gatilhos críticos de curto prazo para detecção de Tilt")

from typing import List

class DiagnosticReport(BaseModel):
    status_variancia: str = Field(..., description="Resumo do status da variância e anomalia (ex: 'Flutuação Normal', 'Zona Amarela', 'Zona Crítica')")
    nivel_gravidade: int = Field(..., ge=1, le=5, description="Nível de gravidade do desvio matemático de 1 a 5")
    red_flags: List[str] = Field(..., description="Lista de anomalias detectadas nos dados (ex: 'VPIP aumentou 6%', 'Downswing de 180bb')")
    diretriz_investigacao: str = Field(..., description="Diretriz para o Agente 2 conduzir a entrevista socrática neutra (ex: 'Questione a mudança de range')")

class FinalBehavioralReport(BaseModel):
    admitiu_erro: bool = Field(..., description="O jogador reconheceu as falhas apontadas?")
    nivel_negacao: int = Field(..., ge=1, le=5, description="Nível de negação ou resistência do jogador (1 a 5)")
    conclusao_entrevista: str = Field(..., description="Resumo da justificativa dada pelo jogador durante o chat")
    recomendacao_coach: str = Field(..., description="Recomendação de ação para o jogador (ex: 'Pausar o jogo por 2 dias')")
