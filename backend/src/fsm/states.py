from typing import Tuple, Optional
from dataclasses import replace
from src.domain.models import HandContext, Action, Street, ActionType
from src.parser.tokenizer import Token, HandStartEvent, StreetChangeEvent, RawActionEvent, CardsRevealedEvent, PotSummaryEvent

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
        if isinstance(token, PotSummaryEvent) and context is not None:
            new_context = replace(
                context, 
                total_pot=token.total_pot, 
                rake=token.rake, 
                jackpot=token.jackpot, 
                bingo=token.bingo, 
                fortune=token.fortune, 
                tax=token.tax
            )
            return self, new_context

        if isinstance(token, RawActionEvent) and context is not None:
            action_enum = _map_action_type(token.action_type)
            if action_enum == ActionType.COLLECT:
                action = Action(
                    player=token.player, 
                    action_type=action_enum, 
                    amount=token.amount,
                    street=context.actions[-1].street if context.actions else Street.RIVER,
                    is_all_in=token.is_all_in,
                    invested_amount=token.amount
                )
                new_context = context.add_action(action)
                return self, new_context

        return self, context

class BaseStreetState(State):
    street: Street
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, RawActionEvent):
            action_enum = _map_action_type(token.action_type)
            
            # Calcula a quantia exata (incremental) gasta
            actions_on_street = [a for a in context.actions if a.street == self.street]
            
            if action_enum == ActionType.RAISE:
                previous_invested = sum(a.invested_amount for a in actions_on_street if a.player == token.player)
                invested_amount = token.amount - previous_invested
            else:
                invested_amount = token.amount
                
            # Cálculo de Pot Odds
            highest_bet = max([a.amount for a in actions_on_street if a.action_type in (ActionType.POST, ActionType.BET, ActionType.RAISE)] + [0.0])
            previous_invested_for_odds = sum(a.invested_amount for a in actions_on_street if a.player == token.player)
            
            amount_to_call = max(0.0, highest_bet - previous_invested_for_odds)
            pot_before_action = context.current_pot
            
            pot_odds = 0.0
            if amount_to_call > 0 and action_enum in (ActionType.CALL, ActionType.FOLD, ActionType.RAISE):
                pot_odds = amount_to_call / (pot_before_action + amount_to_call)

            action = Action(
                player=token.player, 
                action_type=action_enum, 
                amount=token.amount,
                street=self.street,
                is_all_in=token.is_all_in,
                invested_amount=round(invested_amount, 2),
                pot_odds=round(pot_odds * 100, 2)
            )
            new_context = context.add_action(action)
            
            return self, new_context

        elif isinstance(token, CardsRevealedEvent):
            return self, context.set_player_cards(token.player, token.cards)

        elif isinstance(token, HandStartEvent):
            return InitState().process(token, None)

        elif isinstance(token, PotSummaryEvent):
            new_context = replace(
                context, 
                total_pot=token.total_pot, 
                rake=token.rake, 
                jackpot=token.jackpot, 
                bingo=token.bingo, 
                fortune=token.fortune, 
                tax=token.tax
            )
            return TerminalState(), new_context

        return self, context

class RiverState(BaseStreetState):
    street = Street.RIVER

class TurnState(BaseStreetState):
    street = Street.TURN
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, StreetChangeEvent) and token.street_name == "RIVER":
            new_context = replace(context, board_cards=tuple(token.cards))
            return RiverState(), new_context
        return super().process(token, context)

class FlopState(BaseStreetState):
    street = Street.FLOP
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, StreetChangeEvent) and token.street_name == "TURN":
            new_context = replace(context, board_cards=tuple(token.cards))
            return TurnState(), new_context
        return super().process(token, context)

class PreFlopState(BaseStreetState):
    street = Street.PRE_FLOP
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, StreetChangeEvent) and token.street_name == "FLOP":
            new_context = replace(context, board_cards=tuple(token.cards))
            return FlopState(), new_context
        return super().process(token, context)

class InitState(State):
    def __init__(self, platform: str = "", hero_name: str = ""):
        self.platform = platform
        self.hero_name = hero_name

    def process(self, token: Token, context: Optional[HandContext]) -> Tuple[State, Optional[HandContext]]:
        if isinstance(token, HandStartEvent):
            data_capturada = getattr(token, "timestamp", "")
            game_info = getattr(token, "game_info", "")
            stake_level = getattr(token, "stake_level", 0.0)
            new_context = HandContext(
                hand_id=token.hand_id, 
                timestamp=data_capturada, 
                game_info=game_info, 
                stake_level=stake_level,
                platform=self.platform,
                player_nickname=self.hero_name
            )
            return PreFlopState(), new_context
        return self, context