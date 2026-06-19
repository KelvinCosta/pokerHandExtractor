import pytest
from unittest.mock import MagicMock, mock_open, patch
from pathlib import Path
from dataclasses import replace
import json
import sys
import os

# Adiciona a raiz do projeto ao path do Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extractor import process_stream, main
from src.parser.tokenizer import GGPokerTokenizer
from src.domain.models import ActionType
from src.fsm.states import InitState

@pytest.fixture
def tokenizer():
    return GGPokerTokenizer()

@pytest.fixture
def initial_state():
    return InitState()

def test_process_stream_no_actions(tokenizer, initial_state):
    """Testa se o stream não retorna nada quando não há tokens válidos."""
    stream = [
        "Uma linha qualquer sem sentido\n",
        "Outra linha invalida de log\n"
    ]
    
    # Passa diretamente a lista de strings
    results = list(process_stream(stream, "test_log.txt", tokenizer, initial_state))
        
    assert len(results) == 0

def test_process_stream_with_actions(tokenizer, initial_state):
    """Testa se o HandContext é yieldado (retornado) quando uma nova mão inicia."""
    stream = [
        "Poker Hand #RC1: Hold'em No Limit ($0.01/$0.02) - 2026/06/19 10:00:00\n",
        "Hero: calls $0.02\n",
        "Poker Hand #RC2: Hold'em No Limit ($0.01/$0.02) - 2026/06/19 10:01:00\n"
    ]
    
    results = list(process_stream(stream, "test_log.txt", tokenizer, initial_state))
        
    assert len(results) == 1
    hand = results[0]
    assert hand.hand_id == "RC1"
    assert hand.source_file == "test_log.txt"
    assert len(hand.actions) == 1
    assert hand.actions[0].player == "Hero"
    assert hand.actions[0].action_type == ActionType.CALL

def test_process_stream_yields_at_end(tokenizer, initial_state):
    """Testa se o restante do contexto é yieldado ao final do iterador."""
    stream = [
        "Poker Hand #RC1: Hold'em No Limit ($0.01/$0.02) - 2026/06/19 10:00:00\n",
        "Hero: raises $0.02 to $0.04\n"
    ]
    
    results = list(process_stream(stream, "test_log.txt", tokenizer, initial_state))
        
    assert len(results) == 1
    hand = results[0]
    assert hand.hand_id == "RC1"
    assert hand.source_file == "test_log.txt"
    assert len(hand.actions) == 1
    assert hand.actions[0].player == "Hero"
    assert hand.actions[0].action_type == ActionType.RAISE
    assert hand.actions[0].amount == 0.04

@patch("extractor.HandLoader")
@patch("extractor.Path.exists")
@patch("extractor.Path.glob")
def test_main_no_files(mock_glob, mock_exists, mock_loader, capsys):
    """Testa fluxo do main quando não há arquivos .txt na pasta Bronze."""
    mock_exists.return_value = False
    mock_glob.return_value = []
    
    with patch("extractor.os.getenv", return_value="dummy_path"):
        main()
        
    captured = capsys.readouterr()
    assert "Nenhum arquivo .txt encontrado" in captured.out
    mock_loader.assert_not_called()

@patch("extractor.HandLoader")
@patch("extractor.Path.exists")
@patch("extractor.Path.glob")
def test_main_no_new_files(mock_glob, mock_exists, mock_loader, capsys):
    """Testa fluxo do main quando não há ARQUIVOS NOVOS na pasta Bronze."""
    mock_exists.return_value = True
    mock_glob.return_value = [Path("file1.txt")]
    
    with patch("builtins.open", mock_open(read_data=json.dumps(["file1.txt"]))), \
         patch("extractor.os.getenv", return_value="dummy_path"):
        main()
        
    captured = capsys.readouterr()
    assert "Nenhum arquivo novo para extrair" in captured.out
    mock_loader.assert_not_called()

@patch("extractor.HandLoader")
@patch("extractor.Path.exists")
@patch("extractor.Path.glob")
def test_main_with_new_files(mock_glob, mock_exists, mock_loader, capsys):
    """Testa fluxo do main processando um novo arquivo."""
    mock_exists.return_value = True
    mock_glob.return_value = [Path("file1.txt"), Path("new_file.txt")]
    
    # Simula log já processado contém file1.txt
    mock_file = mock_open(read_data=json.dumps(["file1.txt"]))
    
    mock_loader_instance = MagicMock()
    mock_loader.return_value = mock_loader_instance
    mock_loader_instance.process_and_save.return_value = 1
    
    with patch("builtins.open", mock_file), \
         patch("extractor.os.getenv", return_value="dummy_path"), \
         patch("extractor.process_stream", return_value=iter([])) as mock_process:
        
        main()
        
    captured = capsys.readouterr()
    assert "Iniciando Processamento Stream (1 novos arquivos encontrados)" in captured.out
    assert "ETL incremental concluído com sucesso!" in captured.out
    
    mock_loader.assert_called_once()
    mock_loader_instance.process_and_save.assert_called_once()
    
    # Verifica se salvou o log final
    mock_file().write.assert_called()
