import pytest
import sys
import os
import polars as pl
from unittest.mock import patch, MagicMock
from datetime import date

# Adiciona a raiz do projeto ao path do Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa os módulos
from src.dashboard.data_loader import load_data, get_base_dataframe
import streamlit as st

@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Garante que o cache do Streamlit seja limpo entre os testes para evitar efeitos colaterais."""
    st.cache_data.clear()

def test_load_data():
    """Testa se o load_data coleta os parquets, remove as mãos duplicadas e realiza o unnest nas ações."""
    # Simulando um dataframe bruto que o polars.scan_parquet().collect() retornaria
    df_mock = pl.DataFrame({
        "hand_id": ["1", "1", "2"], # Mão 1 duplicada para testar o drop_duplicates (keep=last)
        "actions": [
            [{"player": "Hero", "action_type": "BET", "amount": 10.0}],  # Primeira ocorrência (será descartada)
            [{"player": "Hero", "action_type": "BET", "amount": 10.0}],  # Ocorrência mantida
            [{"player": "Villain", "action_type": "CALL", "amount": 20.0}, 
             {"player": "Hero", "action_type": "FOLD", "amount": 0.0}]   # Array múltiplo
        ]
    })
    
    mock_scan = MagicMock()
    mock_scan.collect.return_value = df_mock
    
    with patch("src.dashboard.data_loader.pl.scan_parquet", return_value=mock_scan):
        df_result = load_data()
        
        # Verifica se descartou a mão 1 duplicada e se explodiu a mão 2 (2 ações)
        # Total final = 1 ação (mão 1) + 2 ações (mão 2) = 3 linhas
        assert df_result.height == 3
        assert "hand_id" in df_result.columns
        
        # Verifica se o unnest ("actions") trouxe as chaves internas para colunas principais
        assert "player" in df_result.columns
        assert "action_type" in df_result.columns
        assert "amount" in df_result.columns
        
        # Verifica especificamente se a mão 2 tem 2 linhas agora
        assert df_result.filter(pl.col("hand_id") == "2").height == 2

def test_get_base_dataframe_with_date_column():
    """Testa a função de preparo base quando a coluna de data oficial é chamada de 'date'."""
    df_mock = pl.DataFrame({
        "hand_id": ["1"],
        "date": ["2026/06/19 12:30:00"]
    })
    
    with patch("src.dashboard.data_loader.load_data", return_value=df_mock):
        df_result, col_name = get_base_dataframe()
        
        assert col_name == "date"
        assert "data_limpa" in df_result.columns
        # Valida se a conversão dt.date() do Polars cortou o timestamp para ter apenas Ano-Mês-Dia
        assert df_result["data_limpa"][0] == date(2026, 6, 19)

def test_get_base_dataframe_with_timestamp_column():
    """Testa o preparo base quando a coluna de data é chamada de 'timestamp' (ex. formato antigo)."""
    df_mock = pl.DataFrame({
        "hand_id": ["1"],
        "timestamp": ["2026/06/19 12:30:00"]
    })
    
    with patch("src.dashboard.data_loader.load_data", return_value=df_mock):
        df_result, col_name = get_base_dataframe()
        
        assert col_name == "timestamp"
        assert "data_limpa" in df_result.columns
        assert df_result["data_limpa"][0] == date(2026, 6, 19)

def test_get_base_dataframe_without_date():
    """Testa a robustez da função caso não exista coluna de data na extração."""
    df_mock = pl.DataFrame({
        "hand_id": ["1"],
        "info": ["qualquer"]
    })
    
    with patch("src.dashboard.data_loader.load_data", return_value=df_mock):
        df_result, col_name = get_base_dataframe()
        
        assert col_name is None
        assert "data_limpa" not in df_result.columns
