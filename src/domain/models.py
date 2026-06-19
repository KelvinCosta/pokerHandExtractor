from dataclasses import dataclass, field, replace
from typing import Tuple, Mapping
from enum import Enum, auto

class Street(Enum):
    PRE_FLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()

class ActionType(Enum):
    POST = auto()
    FOLD = auto()
    CHECK = auto()
    CALL = auto()
    BET = auto()
    RAISE = auto()
    COLLECT = auto()

@dataclass(frozen=True, slots=True)
class Action:
    player: str
    action_type: ActionType
    street: Street 
    amount: float = 0.0
    is_all_in: bool = False
    invested_amount: float = 0.0
    pot_odds: float = 0.0

@dataclass(frozen=True, slots=True)
class HandContext:
    hand_id: str
    timestamp: str
    actions: Tuple[Action, ...] = field(default_factory=tuple)
    board_cards: Tuple[str, ...] = field(default_factory=tuple)
    player_cards: Mapping[str, str] = field(default_factory=dict)
    source_file: str = ""
    total_pot: float = 0.0
    rake: float = 0.0
    jackpot: float = 0.0
    bingo: float = 0.0
    fortune: float = 0.0
    tax: float = 0.0

    @property
    def current_pot(self) -> float:
        return sum(action.invested_amount for action in self.actions if action.action_type not in (ActionType.COLLECT, ActionType.FOLD))

    def add_action(self, action: Action) -> 'HandContext':
        return replace(self, actions=self.actions + (action,))
    
    def set_player_cards(self, player: str, cards: str) -> 'HandContext':
        new_cards = dict(self.player_cards)
        new_cards[player] = cards
        return replace(self, player_cards=new_cards)