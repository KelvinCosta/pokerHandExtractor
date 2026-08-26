import pytest
import sys
import os

# Adiciona a raiz do projeto ao path do Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parser.tokenizer import (
    HandStartEvent, ButtonInfoEvent, SeatInfoEvent, StreetChangeEvent,
    RawActionEvent, CardsRevealedEvent, PotSummaryEvent, EVEvent, TokenizerFactory
)
from src.parser.tokenizers.ggpoker import GGPokerTokenizer

@pytest.fixture
def tokenizer():
    return GGPokerTokenizer()

def test_parse_hand_start(tokenizer):
    line = "Poker Hand #RC113123123: Hold'em No Limit ($0.01/$0.02) - 2026/06/19 10:00:00"
    token = tokenizer.parse_line(line)
    
    assert isinstance(token, HandStartEvent)
    assert token.hand_id == "RC113123123"
    assert token.timestamp == "2026/06/19 10:00:00"

def test_parse_street_change(tokenizer):
    lines = {
        "*** FLOP *** [Ah Kd 2s]": ("FLOP", ["Ah", "Kd", "2s"]),
        "*** TURN *** [Ah Kd 2s] [5c]": ("TURN", ["Ah", "Kd", "2s", "5c"]),
        "*** RIVER *** [Ah Kd 2s 5c] [9h]": ("RIVER", ["Ah", "Kd", "2s", "5c", "9h"])
    }
    
    for line, (expected_street, expected_cards) in lines.items():
        token = tokenizer.parse_line(line)
        assert isinstance(token, StreetChangeEvent)
        assert token.street_name == expected_street
        assert token.cards == expected_cards

def test_parse_actions(tokenizer):
    test_cases = [
        ("Player1: folds", "Player1", "FOLD", 0.0, False),
        ("Player2: checks", "Player2", "CHECK", 0.0, False),
        ("Player3: calls $1.50", "Player3", "CALL", 1.50, False),
        ("Player4: bets $2.00", "Player4", "BET", 2.00, False),
        ("Player5: raises $2.00 to $4.00", "Player5", "RAISE", 4.00, False),
        ("Player6: posts small blind $0.01", "Player6", "POST", 0.01, False),
        ("Player7: posts big blind $0.02", "Player7", "POST", 0.02, False),
        ("Hero: bets $10.00 and is all-in", "Hero", "BET", 10.00, True),
        ("Villain: calls $10.00 and is all-in", "Villain", "CALL", 10.00, True)
    ]
    
    for line, player, action_type, amount, is_all_in in test_cases:
        token = tokenizer.parse_line(line)
        assert isinstance(token, RawActionEvent), f"Falha na linha: {line}"
        assert token.player == player
        assert token.action_type == action_type
        assert token.amount == amount
        assert token.is_all_in == is_all_in

def test_parse_cards_revealed(tokenizer):
    test_cases = [
        ("Dealt to Hero [As Ks]", "Hero", "As Ks"),
        ("Villain: shows [Qc Qh] (Two Pair)", "Villain", "Qc Qh"),
        ("Player3: mucks [2h 3d]", "Player3", "2h 3d")
    ]
    
    for line, player, cards in test_cases:
        token = tokenizer.parse_line(line)
        assert isinstance(token, CardsRevealedEvent)
        assert token.player == player
        assert token.cards == cards

def test_parse_collect_and_uncalled(tokenizer):
    test_cases = [
        ("Hero collected $5.50 from pot", "Hero", "COLLECT", 5.50),
        ("Villain collected $10.00 from main pot", "Villain", "COLLECT", 10.00),
        ("Uncalled bet ($2.50) returned to PlayerX", "PlayerX", "COLLECT", 2.50)
    ]
    
    for line, player, action_type, amount in test_cases:
        token = tokenizer.parse_line(line)
        assert isinstance(token, RawActionEvent)
        assert token.player == player
        assert token.action_type == action_type
        assert token.amount == amount

def test_parse_pot_summary(tokenizer):
    line = "Total pot $10.50 | Rake $0.50 | Jackpot $0.00 | Bingo $0.10 | Fortune $0.00 | Tax $0.00"
    token = tokenizer.parse_line(line)
    
    assert isinstance(token, PotSummaryEvent)
    assert token.total_pot == 10.50
    assert token.rake == 0.50
    assert token.bingo == 0.10
    assert token.jackpot == 0.00
    
    # Teste para summary mais simples
    line_simple = "Total pot $5.00 | Rake $0.25"
    token_simple = tokenizer.parse_line(line_simple)
    
    assert isinstance(token_simple, PotSummaryEvent)
    assert token_simple.total_pot == 5.00
    assert token_simple.rake == 0.25
    assert token_simple.jackpot == 0.00  # Default

def test_parse_empty_or_invalid_lines(tokenizer):
    invalid_lines = [
        "",
        "   ",
        "Alguma linha aleatória do log do poker"
    ]
    
    for line in invalid_lines:
        assert tokenizer.parse_line(line) is None
