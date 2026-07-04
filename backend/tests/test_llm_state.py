import pytest
import polars as pl
import os
import json
from pathlib import Path
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db.warehouse import DuckDBWarehouse
from src.llm.state_builder import SessionStateCalculator

@pytest.fixture
def temp_silver_layer(tmp_path):
    # Simula a estrutura da camada Silver
    silver_dir = tmp_path / "silver"
    silver_dir.mkdir()
    
    # Criar um DataFrame similar ao do loader.py
    # actions é List[Struct]
    
    hands_data = [
        {
            "hand_id": "1",
            "date": "2026/06/19 10:00:00",
            "hero_ganhou": True,
            "actions": [
                {"player": "Hero", "action_type": "BET", "amount": 10.0, "invested_amount": 10.0},
                {"player": "Villain", "action_type": "FOLD", "amount": 0.0, "invested_amount": 0.0},
                {"player": "Hero", "action_type": "COLLECT", "amount": 20.0, "invested_amount": 10.0}
            ],
            "board_cards": ["Ah", "Kd", "Qs", "2c", "5h"]
        },
        {
            "hand_id": "2",
            "date": "2026/06/19 10:02:00",
            "hero_ganhou": False,
            "actions": [
                {"player": "Hero", "action_type": "RAISE", "amount": 30.0, "invested_amount": 30.0},
                {"player": "Villain", "action_type": "CALL", "amount": 30.0, "invested_amount": 30.0}
            ], # Perdeu no showdown
            "board_cards": ["2h", "2d", "2s", "3c", "3h"]
        },
        {
            "hand_id": "3",
            "date": "2026/06/19 10:04:00",
            "hero_ganhou": False,
            "actions": [
                {"player": "Hero", "action_type": "FOLD", "amount": 0.0, "invested_amount": 5.0}
            ], # Perdeu sem showdown
            "board_cards": ["Ah", "Kd", "Qs"]
        }
    ]
    
    df = pl.DataFrame(hands_data)
    df.write_parquet(silver_dir / "hands_part_0001.parquet")
    
    return str(silver_dir)

def test_llm_state_calculation(temp_silver_layer):
    warehouse = DuckDBWarehouse(silver_dir=temp_silver_layer)
    calculator = SessionStateCalculator(warehouse, baseline_agressiveness=0.45)
    
    # Executa o cálculo para as últimas 20 mãos (temos apenas 3)
    state = calculator.get_current_state(hero_name="Hero", num_hands=20)
    
    # 1. Profit da sessão: 
    # Mão 1: Investiu 10, Coletou 20 => Lucro = +10
    # Mão 2: Investiu 30, Coletou 0 => Lucro = -30
    # Mão 3: Investiu 5, Coletou 0 => Lucro = -5
    # Profit total esperado: -25
    assert state["current_session_profit"] == -25.0
    
    # 2. Agressiveness Deviation
    # Ações do Hero:
    # M1: BET (Agressivo)
    # M2: RAISE (Agressivo)
    # M3: FOLD (Passivo)
    # Total ações (ignorando COLLECT): 3. Agressivas = 2. Agressiveness = 2/3 = 0.666
    # Deviation = 0.666 - 0.45 = 0.216...
    assert pytest.approx(state["agressiveness_deviation"], 0.01) == (2/3) - 0.45
    
    # 3. Showdown Frequency
    # Mão 1: Chegou ao River? Tem 5 cartas no board -> Sim (Showdown)
    # Mão 2: 5 cartas -> Sim (Showdown)
    # Mão 3: 3 cartas -> Não
    # Frequência = 2 / 3 = 0.666...
    assert pytest.approx(state["showdown_frequency"], 0.01) == (2/3)
    
    # 4. Consecutive losses
    # A última mão em ordem cronológica foi a 3 (Perdeu), antes a 2 (Perdeu). A 1 ele ganhou.
    # Perdas consecutivas = 2
    assert state["consecutive_losses"] == 2
