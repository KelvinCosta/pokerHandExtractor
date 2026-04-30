from typing import Tuple, Optional
from src.domain.models import HandContext, Action
from src.parser.tokenizer import Token, HandStartEvent, StreetChangeEvent, RawActionEvent

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
            action = Action(player=token.player, action_type=token.action_type, amount=token.amount)
            return self, context.add_action(action)
        # Se vier qualquer outra coisa depois das ações do river (como o fim da leitura), vamos para Terminal
        return TerminalState(), context

class TurnState(State):
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, RawActionEvent):
            action = Action(player=token.player, action_type=token.action_type, amount=token.amount)
            return self, context.add_action(action)
        elif isinstance(token, StreetChangeEvent) and token.street_name == "RIVER":
            from dataclasses import replace
            new_context = replace(context, board_cards=context.board_cards + tuple(token.cards))
            return RiverState(), new_context
        return self, context

class FlopState(State):
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, RawActionEvent):
            action = Action(player=token.player, action_type=token.action_type, amount=token.amount)
            return self, context.add_action(action)
        elif isinstance(token, StreetChangeEvent) and token.street_name == "TURN":
            from dataclasses import replace
            new_context = replace(context, board_cards=context.board_cards + tuple(token.cards))
            return TurnState(), new_context
        return self, context

class PreFlopState(State):
    def process(self, token: Token, context: HandContext) -> Tuple[State, HandContext]:
        if isinstance(token, RawActionEvent):
            action = Action(player=token.player, action_type=token.action_type, amount=token.amount)
            return self, context.add_action(action)
        elif isinstance(token, StreetChangeEvent) and token.street_name == "FLOP":
            # O Flop virou! Atualizamos as cartas comunitárias e trocamos o estado.
            from dataclasses import replace
            new_context = replace(context, board_cards=context.board_cards + tuple(token.cards))
            return FlopState(), new_context
        return self, context

class InitState(State):
    """Estado inicial que aguarda o HandStartEvent para criar o Contexto Base."""
    def process(self, token: Token, context: Optional[HandContext]) -> Tuple[State, Optional[HandContext]]:
        if isinstance(token, HandStartEvent):
            # Cria o cérebro imutável da mão (ainda vazio, mas instanciado)
            new_context = HandContext(
                hand_id=token.hand_id,
                table_name="Unknown", # Por enquanto fixo, depois extraímos se precisar
                button_seat=0         # Por enquanto fixo
            )
            # Transita imediatamente para o Pré-Flop
            return PreFlopState(), new_context
        return self, context