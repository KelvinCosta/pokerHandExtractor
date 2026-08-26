import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parser.tokenizers.pokerstars import PokerStarsTokenizer
from src.parser.tokenizer import HandStartEvent, ButtonInfoEvent, SeatInfoEvent, StreetChangeEvent, RawActionEvent

@pytest.fixture
def tokenizer():
    return PokerStarsTokenizer(hero_name="Hero")

def test_parse_hand_start(tokenizer):
    line = "PokerStars Hand #215904000:  Hold'em No Limit ($0.01/$0.02 USD) - 2026/06/19 10:00:00 ET"
    token = tokenizer.parse_line(line)
    assert isinstance(token, HandStartEvent)
    assert token.hand_id == "215904000"
    assert token.stake_level == 0.02

def test_parse_button(tokenizer):
    line = "Table 'A' 6-max Seat #1 is the button"
    token = tokenizer.parse_line(line)
    assert isinstance(token, ButtonInfoEvent)
    assert token.button_seat == 1

def test_parse_seat(tokenizer):
    line = "Seat 1: PlayerA ($10.50 in chips)"
    token = tokenizer.parse_line(line)
    assert isinstance(token, SeatInfoEvent)
    assert token.seat == 1
    assert token.player == "PlayerA"
    assert token.starting_stack == 10.50

def test_parse_action(tokenizer):
    line = "PlayerA: raises $0.04 to $0.06"
    token = tokenizer.parse_line(line)
    assert isinstance(token, RawActionEvent)
    assert token.player == "PlayerA"
    assert token.action_type == "RAISE"
    assert token.amount == 0.06
