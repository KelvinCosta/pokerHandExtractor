from datetime import datetime
from pydantic import BaseModel, Field

class TimeWindow(BaseModel):
    start_date: datetime = Field(..., description="Início da janela de tempo analisada")
    end_date: datetime = Field(..., description="Fim da janela de tempo analisada")

class PlayerStats(BaseModel):
    player_id: str = Field(..., description="Identificador único do jogador")
    financial_profit: float = Field(..., description="Lucro financeiro total no período (em USD ou BB)")
    aggressiveness_factor: float = Field(..., description="Fator de agressividade (AF) calculado")
    showdown_frequency: float = Field(..., description="Frequência de ida ao Showdown (WTSD%)", ge=0.0, le=100.0)
    consecutive_wins: int = Field(0, description="Número de vitórias consecutivas atuais", ge=0)
    consecutive_losses: int = Field(0, description="Número de derrotas consecutivas atuais", ge=0)
    time_window: TimeWindow = Field(..., description="Metadados da janela de tempo")
    
    model_config = {
        "frozen": True,  # Garante a imutabilidade do modelo
        "extra": "forbid" # Impede injeção de campos não mapeados
    }
