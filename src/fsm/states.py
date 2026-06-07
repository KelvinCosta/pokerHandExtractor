from typing import Tuple, Optional
from dataclasses import replace
from src.domain.models import HandContext, Action, Street, ActionType
from src.parser.tokenizer import Token, HandStartEvent, StreetChangeEvent, RawActionEvent, CardsRevealedEvent

def _map_action_type(raw_action: str) -> ActionType:
    try:
        return ActionType[raw_action]
    except KeyError:
        return ActionType.CALL 

class State:
    def process(self, token: Token, context: Optional[HandContext]) -> Tuple['State', Optional[HandContext]]:
        raise NotImplementedError("Cada estado deve implementar seu próprio processamento.")

class TerminalState(State):
    def process(self, token: Token, context: Optional[HandContext]) -> Tuple['State', Optional[HandContext]]:
        return self, context

class BaseStreetState(State):
    street: Street

    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, RawActionEvent):
            action_enum = _map_action_type(token.action_type)
            action = Action(
                player=token.player, 
                action_type=action_enum, 
                amount=token.amount,
                street=self.street
            )
            new_context = context.add_action(action)
            
            if action_enum == ActionType.COLLECT:
                return TerminalState(), new_context
                
            return self, new_context

        elif isinstance(token, CardsRevealedEvent):
            return self, context.set_player_cards(token.player, token.cards)

        elif isinstance(token, HandStartEvent):
            return InitState().process(token, None)

        return self, context

class RiverState(BaseStreetState):
    street = Street.RIVER

class TurnState(BaseStreetState):
    street = Street.TURN
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, StreetChangeEvent) and token.street_name == "RIVER":
            new_context = replace(context, board_cards=context.board_cards + tuple(token.cards))
            return RiverState(), new_context
        return super().process(token, context)

class FlopState(BaseStreetState):
    street = Street.FLOP
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, StreetChangeEvent) and token.street_name == "TURN":
            new_context = replace(context, board_cards=context.board_cards + tuple(token.cards))
            return TurnState(), new_context
        return super().process(token, context)

class PreFlopState(BaseStreetState):
    street = Street.PRE_FLOP
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, StreetChangeEvent) and token.street_name == "FLOP":
            new_context = replace(context, board_cards=context.board_cards + tuple(token.cards))
            return FlopState(), new_context
        return super().process(token, context)

class InitState(State):
    def process(self, token: Token, context: Optional[HandContext]) -> Tuple[State, Optional[HandContext]]:
        if isinstance(token, HandStartEvent):
            data_capturada = getattr(token, "timestamp", "")
            new_context = HandContext(hand_id=token.hand_id, timestamp=data_capturada)
            return PreFlopState(), new_context
        return self, context