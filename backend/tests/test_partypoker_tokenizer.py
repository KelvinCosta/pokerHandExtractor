import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parser.tokenizers.partypoker import PartyPokerTokenizer
from src.parser.tokenizer import HandStartEvent, ButtonInfoEvent, SeatInfoEvent, StreetChangeEvent, RawActionEvent

@pytest.fixture
def tokenizer():
    return PartyPokerTokenizer(hero_name="Hero")

def test_parse_hand_start(tokenizer):
    line = "***** Hand History for Game 123456 *****"
    token = tokenizer.parse_line(line)
    assert isinstance(token, HandStartEvent)
    assert token.hand_id == "123456"

def test_parse_button(tokenizer):
    line = "Seat 1 is the button"
    token = tokenizer.parse_line(line)
    assert isinstance(token, ButtonInfoEvent)
    assert token.button_seat == 1

def test_parse_seat(tokenizer):
    line = "Seat 1: PlayerA ( $1,000 USD )"
    token = tokenizer.parse_line(line)
    assert isinstance(token, SeatInfoEvent)
    assert token.seat == 1
    assert token.player == "PlayerA"
    assert token.starting_stack == 1000.0

def test_parse_action(tokenizer):
    line = "PlayerA raises [ $100 USD ]"
    token = tokenizer.parse_line(line)
    assert isinstance(token, RawActionEvent)
    assert token.player == "PlayerA"
    assert token.action_type == "RAISE"
    assert token.amount == 100.0
