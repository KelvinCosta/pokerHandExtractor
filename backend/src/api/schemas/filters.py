from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class DashboardFilters(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    start_date: Optional[date] = Field(None, description="Data inicial do filtro")
    end_date: Optional[date] = Field(None, description="Data final do filtro")
    game_types: Optional[List[str]] = Field(None, description="Lista de tipos de jogo (ex: ['Rush & Cash'])")
    stake: Optional[float] = Field(None, description="Filtro específico por nível de aposta")
    hero_name: Optional[str] = Field("Hero", description="Nome do jogador base")
