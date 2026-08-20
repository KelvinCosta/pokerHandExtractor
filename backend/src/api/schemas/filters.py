from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class DashboardFilters(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    start_date: Optional[date] = Field(None, description="Data inicial do filtro")
    end_date: Optional[date] = Field(None, description="Data final do filtro")
    game_types: Optional[List[str]] = Field(None, description="Lista de tipos de jogo (ex: ['Rush & Cash'])")
    stake: Optional[str] = Field(None, description="Filtro específico por nível de aposta (ex: 'NL10' ou 'Micro')")
    hero_name: Optional[str] = Field("Hero", description="Nome do jogador base")
    platforms: Optional[List[str]] = Field(None, description="Lista de plataformas para filtrar (ex: ['ggpoker'])")
    search_query: Optional[str] = Field(None, description="Filtro de busca textual (ex: ID da mão ou nick do vilão)")
    hole_cards_range: Optional[str] = Field(None, description="Filtro de range pré-flop (ex: 'AKs')")
    hero_position: Optional[str] = Field(None, description="Posição do hero (ex: 'BTN')")

class HandsListFilters(DashboardFilters):
    page: int = Field(1, description="Página atual")
    limit: int = Field(20, description="Quantidade de itens por página")
    sort_by: str = Field("timestamp", description="Coluna para ordenar (ex: 'timestamp', 'pot_in_bb', 'net_profit')")
    sort_desc: bool = Field(True, description="Ordem decrescente")
