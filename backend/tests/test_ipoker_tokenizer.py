import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parser.tokenizers.ipoker import IPokerTokenizer
from src.parser.tokenizer import HandStartEvent, ButtonInfoEvent, SeatInfoEvent, StreetChangeEvent, RawActionEvent

@pytest.fixture
def tokenizer():
    return IPokerTokenizer(hero_name="Hero")

def test_parse_hand_start(tokenizer):
    line = '<game gamecode="123456789">'
    token = tokenizer.parse_line(line)
    assert isinstance(token, HandStartEvent)
    assert token.hand_id == "123456789"

def test_parse_seat(tokenizer):
    line = '<player seat="1" name="PlayerA" chips="1000" dealer="1" />'
    token = tokenizer.parse_line(line)
    assert isinstance(token, SeatInfoEvent)
    assert token.seat == 1
    assert token.player == "PlayerA"
    assert token.starting_stack == 1000.0

def test_parse_action(tokenizer):
    line = '<action player="PlayerA" type="23" sum="10" />'
    token = tokenizer.parse_line(line)
    assert isinstance(token, RawActionEvent)
    assert token.player == "PlayerA"
    assert token.action_type == "RAISE"
    assert token.amount == 10.0
