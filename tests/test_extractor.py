import pytest
from unittest.mock import MagicMock, mock_open, patch
from pathlib import Path
from dataclasses import replace
import json
import sys
import os

# Adiciona a raiz do projeto ao path do Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extractor import process_file_stream, main
from src.parser.tokenizer import HandStartEvent, RawActionEvent
from src.domain.models import HandContext, Action, ActionType, Street

@pytest.fixture
def mock_tokenizer():
    return MagicMock()

@pytest.fixture
def mock_initial_state():
    return MagicMock()

def test_process_file_stream_no_actions(mock_tokenizer, mock_initial_state):
    """Testa se o stream não retorna nada quando não há tokens válidos."""
    filepath = Path("test_log.txt")
    mock_file_content = "Line 1\nLine 2"
    
    # Mock para não retornar tokens
    mock_tokenizer.parse_line.return_value = None
    
    with patch("builtins.open", mock_open(read_data=mock_file_content)):
        results = list(process_file_stream(filepath, mock_tokenizer, mock_initial_state))
        
    assert len(results) == 0
    assert mock_tokenizer.parse_line.call_count == 2

def test_process_file_stream_with_actions(mock_tokenizer, mock_initial_state):
    """Testa se o HandContext é yieldado (retornado) quando uma nova mão inicia."""
    filepath = Path("test_log.txt")
    mock_file_content = "HandStart\nAction1\nHandStart"
    
    token_start1 = HandStartEvent(hand_id="1", timestamp="2026")
    token_action = RawActionEvent(player="P1", action_type="CALL", amount=10.0)
    token_start2 = HandStartEvent(hand_id="2", timestamp="2026")
    
    mock_tokenizer.parse_line.side_effect = [token_start1, token_action, token_start2]
    
    state1 = MagicMock()
    state2 = MagicMock()
    
    ctx1 = HandContext(hand_id="1", timestamp="2026")
    # Ação pre-flop
    action = Action(player="P1", action_type=ActionType.CALL, street=Street.PRE_FLOP, amount=10.0)
    ctx2 = ctx1.add_action(action)
    
    # Simulando o loop process()
    # 1. token_start1
    # 2. token_action
    # 3. token_start2 -> O contexto anterior tem que ser yieldado aqui
    mock_initial_state.process.side_effect = [
        (state1, ctx1), 
        (state2, ctx2),
        (state1, HandContext(hand_id="2", timestamp="2026"))
    ]
    
    # Correção: precisamos garantir que o state1 retorne o proximo contexto
    # Vamos redefinir o mock baseado em um wrapper simplificado
    def mock_process(token, ctx):
        if isinstance(token, HandStartEvent):
            return state1, HandContext(hand_id=token.hand_id, timestamp="2026")
        elif isinstance(token, RawActionEvent):
            return state1, ctx.add_action(action)
        return state1, ctx
        
    mock_initial_state.process.side_effect = mock_process
    state1.process.side_effect = mock_process

    with patch("builtins.open", mock_open(read_data=mock_file_content)):
        results = list(process_file_stream(filepath, mock_tokenizer, mock_initial_state))
        
    assert len(results) == 1
    assert results[0].hand_id == "1"
    assert results[0].source_file == "test_log.txt"
    assert len(results[0].actions) == 1

def test_process_file_stream_yields_at_end(mock_tokenizer, mock_initial_state):
    """Testa se o restante do contexto é yieldado ao final do arquivo."""
    filepath = Path("test_log.txt")
    mock_file_content = "HandStart\nAction1"
    
    token_start1 = HandStartEvent(hand_id="1", timestamp="2026")
    token_action = RawActionEvent(player="P1", action_type="CALL", amount=10.0)
    
    mock_tokenizer.parse_line.side_effect = [token_start1, token_action]
    
    state1 = MagicMock()
    action = Action(player="P1", action_type=ActionType.CALL, street=Street.PRE_FLOP, amount=10.0)
    
    def mock_process(token, ctx):
        if isinstance(token, HandStartEvent):
            return state1, HandContext(hand_id=token.hand_id, timestamp="2026")
        elif isinstance(token, RawActionEvent):
            return state1, ctx.add_action(action)
        return state1, ctx
        
    mock_initial_state.process.side_effect = mock_process
    state1.process.side_effect = mock_process

    with patch("builtins.open", mock_open(read_data=mock_file_content)):
        results = list(process_file_stream(filepath, mock_tokenizer, mock_initial_state))
        
    assert len(results) == 1
    assert results[0].hand_id == "1"
    assert results[0].source_file == "test_log.txt"
    assert len(results[0].actions) == 1

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
         patch("extractor.process_file_stream", return_value=iter([])) as mock_process:
        
        main()
        
    captured = capsys.readouterr()
    assert "Iniciando Processamento Stream (1 novos arquivos encontrados)" in captured.out
    assert "ETL incremental concluído com sucesso!" in captured.out
    
    mock_loader.assert_called_once()
    mock_loader_instance.process_and_save.assert_called_once()
    
    # Verifica se salvou o log final
    mock_file().write.assert_called()
