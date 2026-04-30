from typing import Tuple, Optional
from src.domain.models import HandContext, Action
from src.parser.tokenizer import Token, HandStartEvent, StreetChangeEvent, RawActionEvent
from src.parser.tokenizer import CardsRevealedEvent

class State:
    """Interface base para os estados da Máquina de Estados."""
    def process(self, token: Token, context: Optional[HandContext]) -> Tuple['State', Optional[HandContext]]:
        raise NotImplementedError("Cada estado deve implementar seu próprio processamento.")

class TerminalState(State):
    """Estado final da mão. Não faz nada, apenas sinaliza o fim."""
    def process(self, token: Token, context: Optional[HandContext]) -> Tuple['State', Optional[HandContext]]:
        return self, context

class RiverState(State):
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, RawActionEvent):
            action = Action(
                player=token.player, 
                action_type=token.action_type, 
                amount=token.amount,
                street="RIVER"
            )
            return self, context.add_action(action)
        elif isinstance(token, CardsRevealedEvent):
            return self, context.set_player_cards(token.player, token.cards)
        return TerminalState(), context

class TurnState(State):
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, RawActionEvent):
            action = Action(
                player=token.player, 
                action_type=token.action_type, 
                amount=token.amount,
                street="TURN"
            )
            return self, context.add_action(action)
        elif isinstance(token, CardsRevealedEvent):
            return self, context.set_player_cards(token.player, token.cards)
        elif isinstance(token, StreetChangeEvent) and token.street_name == "RIVER":
            from dataclasses import replace
            new_context = replace(context, board_cards=context.board_cards + tuple(token.cards))
            return RiverState(), new_context
        return self, context

class FlopState(State):
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, RawActionEvent):
            action = Action(
                player=token.player, 
                action_type=token.action_type, 
                amount=token.amount,
                street="FLOP"
            )
            return self, context.add_action(action)
        elif isinstance(token, CardsRevealedEvent):
            return self, context.set_player_cards(token.player, token.cards)
        elif isinstance(token, StreetChangeEvent) and token.street_name == "TURN":
            from dataclasses import replace
            new_context = replace(context, board_cards=context.board_cards + tuple(token.cards))
            return TurnState(), new_context
        return self, context

class PreFlopState(State):
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, RawActionEvent):
            action = Action(
                player=token.player, 
                action_type=token.action_type, 
                amount=token.amount, 
                street="PREFLOP"
            )
            return self, context.add_action(action)
        elif isinstance(token, CardsRevealedEvent):
            return self, context.set_player_cards(token.player, token.cards)
        elif isinstance(token, StreetChangeEvent) and token.street_name == "FLOP":
            from dataclasses import replace
            new_context = replace(context, board_cards=context.board_cards + tuple(token.cards))
            return FlopState(), new_context
        return self, context

class InitState(State):
    """Estado inicial que aguarda o HandStartEvent para criar o Contexto Base."""
    def process(self, token: Token, context: Optional[HandContext]) -> Tuple[State, Optional[HandContext]]:
        if isinstance(token, HandStartEvent):
            new_context = HandContext(hand_id=token.hand_id)
            return PreFlopState(), new_context
        return self, context