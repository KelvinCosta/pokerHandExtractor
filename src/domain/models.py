from dataclasses import dataclass, field
from typing import Tuple, Optional

@dataclass(frozen=True, slots=True)
class Action:
    """Representa uma ação atômica e imutável de um jogador."""
    player: str
    action_type: str  # Ex: "FOLD", "CALL", "RAISE", "BET", "CHECK"
    amount: float = 0.0

@dataclass(frozen=True, slots=True)
class HandContext:
    """
    O cérebro da mão. Este contexto viajará pelos estados (Pré-flop, Flop, etc).
    Como é frozen, cada mudança de estado deverá retornar uma cópia atualizada deste objeto.
    """
    hand_id: str
    table_name: str
    button_seat: int
    current_pot: float = 0.0
    
    # Usamos Tuple em vez de List para garantir que a coleção de ações também seja imutável
    actions: Tuple[Action, ...] = field(default_factory=tuple)
    
    # Cartas comunitárias reveladas até o momento
    board_cards: Tuple[str, ...] = field(default_factory=tuple)

    def add_action(self, action: Action) -> 'HandContext':
        """
        Gera um NOVO HandContext (cópia) com a nova ação e o pote atualizado,
        respeitando o princípio da imutabilidade.
        """
        # Em Python, o replace() nativo de dataclasses cria uma nova instância
        from dataclasses import replace
        return replace(
            self,
            actions=self.actions + (action,),
            current_pot=self.current_pot + action.amount
        )