from datetime import datetime
from pydantic import BaseModel, Field

class TimeWindow(BaseModel):
    start_date: datetime = Field(..., description="Início da janela de tempo analisada")
    end_date: datetime = Field(..., description="Fim da janela de tempo analisada")
    stake_level: float = Field(..., description="Nível de aposta (ex: 2.0 para NL2, 10.0 para NL10)")

class RecentTrend(BaseModel):
    hands_analyzed: int = Field(..., description="Tamanho da amostra recente (25% das mãos totais)")
    profit_bb: float = Field(..., description="Lucro no bloco recente")
    win_rate_bb100: float = Field(..., description="Win rate no bloco recente")
    vpip: float = Field(..., description="VPIP recente")
    pfr: float = Field(..., description="PFR recente")
    aggressiveness_factor: float = Field(..., description="Fator de agressividade recente")

class PlayerStats(BaseModel):
    player_id: str = Field(..., description="Identificador único do jogador")
    hands_played: int = Field(0, description="Volume de mãos jogadas no período")
    win_rate_bb100: float = Field(0.0, description="Win rate (Lucro em BBs por 100 mãos)")
    vpip: float = Field(0.0, description="Voluntarily Put Money in Pot (%)")
    pfr: float = Field(0.0, description="Pre-Flop Raise (%)")
    all_in_freq: float = Field(0.0, description="Frequência de All-In (%)")
    wsd: float = Field(0.0, description="Won Money at Showdown (W$SD %)")
    wwsf: float = Field(0.0, description="Won When Saw Flop (WWSF %)")
    profit_bb: float = Field(..., description="Lucro total no período em Big Blinds (BB)")
    aggressiveness_factor: float = Field(..., description="Fator de agressividade (AF) calculado")
    showdown_frequency: float = Field(..., description="Frequência de ida ao Showdown (WTSD%)", ge=0.0, le=100.0)
    consecutive_wins: int = Field(0, description="Maior sequência de ganhos contínuos", ge=0)
    consecutive_losses: int = Field(0, description="Maior sequência de perdas contínuas (Sinal vermelho para Tilt)", ge=0)
    time_window: TimeWindow = Field(..., description="Metadados da janela de tempo")
    recent_trend: RecentTrend = Field(..., description="Recorte das últimas 25% de mãos jogadas para detectar desvios de comportamento recentes")
    
    model_config = {
        "frozen": True,  # Garante a imutabilidade do modelo
        "extra": "forbid" # Impede injeção de campos não mapeados
    }
