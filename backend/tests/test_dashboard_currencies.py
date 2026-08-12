import pytest
import polars as pl
from unittest.mock import patch, MagicMock
import asyncio

# Vamos mockar o DataFrame retornado pelos filtros para simular um cenário onde
# o usuário jogou torneios (lucro em fichas) e cash games (lucro em dólares).

@pytest.fixture
def mock_df():
    # Cria um DataFrame simulando dados de mãos
    return pl.DataFrame({
        "hand_id": ["h1", "h2", "h3"],
        "player": ["Vilao", "Vilao", "Outro"],
        "player_nickname": ["Hero", "Hero", "Hero"],
        "hero_net_profit_usd": [0.0, 15.5, -5.0], # Torneio 1, Cash 1, Cash 2
        "hero_net_chips": [5000.0, 0.0, 0.0],     # Torneio 1 lucro de fichas
        "hero_net_profit_bb": [0.0, 15.5, -5.0],
        "stake_level": [0.0, 1.0, 1.0],
        "stake_tier": ["Tournament", "NL100", "NL100"],
        "street": ["PRE_FLOP", "PRE_FLOP", "PRE_FLOP"],
        "action_type": ["FOLD", "FOLD", "FOLD"],
        "game_type": ["Tournament", "Regular Cash", "Regular Cash"]
    })

@pytest.mark.asyncio
@patch("src.api.routers.dashboard.get_filtered_df")
async def test_stake_breakdown_currencies(mock_get_filtered, mock_df):
    from src.api.routers.dashboard import get_stake_breakdown
    from src.api.schemas.filters import DashboardFilters
    from src.database.models import User
    
    mock_get_filtered.return_value = mock_df
    
    filters = DashboardFilters()
    user = User(id="test_user")
    
    result = await get_stake_breakdown(filters, user)
    
    # Devemos ter 2 stakes: "Tournament" e "NL100"
    assert len(result) == 2
    
    # Encontrar as stakes no resultado
    tourney = next(r for r in result if r["stake"] == "Tournament")
    nl100 = next(r for r in result if r["stake"] == "NL100")
    
    # Valida separação de USD e Chips no torneio
    assert tourney["profit_usd"] == 0.0
    assert tourney["profit_chips"] == 5000.0
    
    # Valida separação no Cash Game
    assert nl100["profit_usd"] == 10.5  # 15.5 - 5.0
    assert nl100["profit_chips"] == 0.0

@pytest.mark.asyncio
@patch("src.api.routers.dashboard.get_filtered_df")
async def test_biggest_rivals_currencies(mock_get_filtered, mock_df):
    from src.api.routers.dashboard import get_biggest_rivals
    from src.api.schemas.filters import DashboardFilters
    from src.database.models import User
    
    mock_get_filtered.return_value = mock_df
    
    filters = DashboardFilters()
    user = User(id="test_user")
    
    result = await get_biggest_rivals(filters, user)
    
    # Devemos ter 2 vilões: "Vilao" e "Outro"
    assert len(result) == 2
    
    vilao = next(r for r in result if r["alias"] == "Vilao")
    outro = next(r for r in result if r["alias"] == "Outro")
    
    # Vilao participou da mão 1 (USD 0, Chips 5000) e mão 2 (USD 15.5, Chips 0)
    # Como o "net" do rival inverte o lucro do Hero (Hero ganhou, logo rival perdeu)
    assert vilao["net_usd"] == -15.5
    assert vilao["net_chips"] == -5000.0
    
    # Outro participou da mão 3 (USD -5.0, Chips 0)
    assert outro["net_usd"] == 5.0
    assert outro["net_chips"] == 0.0

@pytest.mark.asyncio
@patch("src.api.routers.dashboard.get_filtered_df")
async def test_analytics_currencies(mock_get_filtered, mock_df):
    from src.api.routers.dashboard import get_analytics_bento
    from src.api.schemas.filters import DashboardFilters
    from src.database.models import User
    
    mock_get_filtered.return_value = mock_df
    
    filters = DashboardFilters()
    user = User(id="test_user")
    
    result = await get_analytics_bento(filters, user)
    
    # O mock_df original não tem lógica avançada de WTSD, WWSF (requer action_type específicos), 
    # mas a red line profit por padrão agrupa tudo se hero_went_to_sd estiver vazio.
    # Neste mock, o Hero não foi pro showdown, então tudo deve cair na red_line.
    assert result["red_line_profit"] == 10.5
    assert result["red_line_chips"] == 5000.0
    
    assert result["blue_line_profit"] == 0.0
    assert result["blue_line_chips"] == 0.0
