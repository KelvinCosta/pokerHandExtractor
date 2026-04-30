from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict

@dataclass(frozen=True, slots=True)
class Action:
    player: str
    action_type: str
    street: str  # PRE-FLOP, FLOP, TURN, RIVER
    amount: float = 0.0

@dataclass(frozen=True, slots=True)
class HandContext:
    hand_id: str
    current_pot: float = 0.0
    actions: Tuple[Action, ...] = field(default_factory=tuple)
    board_cards: Tuple[str, ...] = field(default_factory=tuple)
    # Mapeia Jogador -> Cartas (Ex: {"Hero": "AhKh", "3eeb7226": "Js8s"})
    player_cards: Dict[str, str] = field(default_factory=dict)

    def add_action(self, action: Action) -> 'HandContext':
        from dataclasses import replace
        return replace(
            self,
            actions=self.actions + (action,),
            current_pot=self.current_pot + action.amount
        )
    
    def set_player_cards(self, player: str, cards: str) -> 'HandContext':
        from dataclasses import replace
        new_cards = self.player_cards.copy()
        new_cards[player] = cards
        return replace(self, player_cards=new_cards)