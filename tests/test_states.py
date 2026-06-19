import pytest
import sys
import os

# Adiciona a raiz do projeto ao path do Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fsm.states import (
    InitState, 
    PreFlopState, 
    FlopState, 
    TurnState, 
    RiverState, 
    TerminalState, 
    _map_action_type
)
from src.domain.models import HandContext, ActionType, Street, Action
from src.parser.tokenizer import (
    HandStartEvent,
    StreetChangeEvent,
    RawActionEvent,
    CardsRevealedEvent,
    PotSummaryEvent
)

@pytest.fixture
def empty_context():
    return HandContext(hand_id="123", timestamp="2026/06/19 12:00:00")

def test_map_action_type():
    assert _map_action_type("FOLD") == ActionType.FOLD
    assert _map_action_type("CALL") == ActionType.CALL
    assert _map_action_type("RAISE") == ActionType.RAISE
    # Testa o caso padrão para KeyError
    assert _map_action_type("INVALID_ACTION") == ActionType.CALL

def test_init_state_transition():
    state = InitState()
    token = HandStartEvent(hand_id="RC123", timestamp="2026")
    
    new_state, new_context = state.process(token, None)
    
    assert isinstance(new_state, PreFlopState)
    assert new_context.hand_id == "RC123"
    assert new_context.timestamp == "2026"

def test_preflop_to_flop_transition(empty_context):
    state = PreFlopState()
    token = StreetChangeEvent(street_name="FLOP", cards=["Ah", "Kh", "Qh"])
    
    new_state, new_context = state.process(token, empty_context)
    
    assert isinstance(new_state, FlopState)
    assert new_context.board_cards == ("Ah", "Kh", "Qh")

def test_flop_to_turn_transition():
    state = FlopState()
    empty_context = HandContext(hand_id="1", timestamp="t", board_cards=("Ah", "Kh", "Qh"))
    
    token = StreetChangeEvent(street_name="TURN", cards=["Jh"])
    
    new_state, new_context = state.process(token, empty_context)
    
    assert isinstance(new_state, TurnState)
    assert new_context.board_cards == ("Ah", "Kh", "Qh", "Jh")

def test_turn_to_river_transition():
    state = TurnState()
    empty_context = HandContext(hand_id="1", timestamp="t", board_cards=("Ah", "Kh", "Qh", "Jh"))
    
    token = StreetChangeEvent(street_name="RIVER", cards=["Th"])
    
    new_state, new_context = state.process(token, empty_context)
    
    assert isinstance(new_state, RiverState)
    assert new_context.board_cards == ("Ah", "Kh", "Qh", "Jh", "Th")

def test_action_processing_normal_bet(empty_context):
    state = PreFlopState()
    token = RawActionEvent(player="Hero", action_type="BET", amount=10.0, is_all_in=False)
    
    new_state, new_context = state.process(token, empty_context)
    
    assert new_state is state  # Permanece no mesmo estado de street
    assert len(new_context.actions) == 1
    
    action = new_context.actions[0]
    assert action.player == "Hero"
    assert action.action_type == ActionType.BET
    assert action.amount == 10.0
    assert action.invested_amount == 10.0
    assert action.street == Street.PRE_FLOP
    assert action.is_all_in is False

def test_action_processing_raise_calculation(empty_context):
    state = FlopState()
    
    # 1. Primeira aposta
    token_bet = RawActionEvent(player="Hero", action_type="BET", amount=10.0)
    _, ctx1 = state.process(token_bet, empty_context)
    
    # 2. Villain dá raise pra 30
    token_raise1 = RawActionEvent(player="Villain", action_type="RAISE", amount=30.0)
    _, ctx2 = state.process(token_raise1, ctx1)
    
    # 3. Hero dá re-raise pra 100 (mas já tinha investido 10, então nesta ação ele investe 90)
    token_raise2 = RawActionEvent(player="Hero", action_type="RAISE", amount=100.0)
    _, ctx3 = state.process(token_raise2, ctx2)
    
    actions = ctx3.actions
    assert len(actions) == 3
    
    assert actions[0].invested_amount == 10.0
    assert actions[1].invested_amount == 30.0
    assert actions[2].amount == 100.0
    assert actions[2].invested_amount == 90.0  # (100 - 10)

def test_cards_revealed_processing(empty_context):
    state = RiverState()
    token = CardsRevealedEvent(player="Hero", cards="As Ah")
    
    _, new_context = state.process(token, empty_context)
    
    assert "Hero" in new_context.player_cards
    assert new_context.player_cards["Hero"] == "As Ah"

def test_pot_summary_transition_to_terminal(empty_context):
    state = RiverState()
    token = PotSummaryEvent(total_pot=100.0, rake=5.0, jackpot=1.0, bingo=0.5, fortune=0.0, tax=0.0)
    
    new_state, new_context = state.process(token, empty_context)
    
    assert isinstance(new_state, TerminalState)
    assert new_context.total_pot == 100.0
    assert new_context.rake == 5.0
    assert new_context.jackpot == 1.0
    assert new_context.bingo == 0.5

def test_terminal_state_collect_action(empty_context):
    state = TerminalState()
    
    action_prev = Action(player="Villain", action_type=ActionType.CALL, street=Street.RIVER, amount=10.0)
    ctx1 = empty_context.add_action(action_prev)
    
    token = RawActionEvent(player="Hero", action_type="COLLECT", amount=95.0)
    
    new_state, new_context = state.process(token, ctx1)
    
    assert new_state is state
    assert len(new_context.actions) == 2
    
    collect_action = new_context.actions[-1]
    assert collect_action.player == "Hero"
    assert collect_action.action_type == ActionType.COLLECT
    assert collect_action.amount == 95.0
    assert collect_action.street == Street.RIVER  # Herdou a street da última ação para manter contexto

def test_hand_start_in_middle_of_hand(empty_context):
    """Testa a robustez da FSM: Se iniciar uma nova mão antes de terminar a anterior."""
    state = FlopState()
    token = HandStartEvent(hand_id="NOVA_MAO", timestamp="123")
    
    new_state, new_context = state.process(token, empty_context)
    
    assert isinstance(new_state, PreFlopState)
    assert new_context.hand_id == "NOVA_MAO"
