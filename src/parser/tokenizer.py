import re
from pydantic import BaseModel, Field
from typing import List, Optional, Union

# ==========================================
# 1. CONTRATOS DE DADOS (PYDANTIC)
# ==========================================

class HandStartEvent(BaseModel):
    """Evento disparado quando o parser encontra o cabeçalho de uma nova mão."""
    hand_id: str

class StreetChangeEvent(BaseModel):
    """Evento disparado quando o board vira (Flop, Turn, River)."""
    street_name: str # Ex: "FLOP", "TURN", "RIVER"
    cards: List[str]

class RawActionEvent(BaseModel):
    """Evento disparado quando um jogador age."""
    player: str
    action_type: str
    amount: float = Field(default=0.0, ge=0.0)

# O tipo Token pode ser qualquer um desses três eventos
Token = Union[HandStartEvent, StreetChangeEvent, RawActionEvent]

# ==========================================
# 2. O MOTOR DO TOKENIZADOR
# ==========================================

class GGPokerTokenizer:
    """
    Lê linhas de texto bruto e tenta convertê-las em Eventos Pydantic tipados.
    Atua como Anti-Corruption Layer (ACL).
    """
    def __init__(self):
        # Captura: Poker Hand #RC4095246938: ...
        self.re_hand_start = re.compile(r"^Poker Hand #([a-zA-Z0-9]+):")
        
        # Captura o último colchete da linha. Ex: *** TURN *** [Qs 2h 9s] [6s] -> Pega só o '6s'
        self.re_street = re.compile(r"^\*\*\* (FLOP|TURN|RIVER) \*\*\*.*\[([^\]]+)\]\s*$")
        
        # Captura ações e blinds. O truque `(?:.*?\$([0-9\.]+))?` pega o ÚLTIMO valor em dólar da linha, 
        # perfeito para "raises $0.02 to $0.04"
        self.re_action = re.compile(r"^([^:]+): (folds|calls|raises|bets|checks|posts small blind|posts big blind)(?:.*?\$([0-9\.]+))?")

    def parse_line(self, line: str) -> Optional[Token]:
        line = line.strip()
        if not line:
            return None

        # 1. Tenta casar com Cabeçalho de Mão
        match_start = self.re_hand_start.search(line)
        if match_start:
            return HandStartEvent(hand_id=match_start.group(1))

        # 2. Tenta casar com Mudança de Rua (Flop, Turn, River)
        match_street = self.re_street.search(line)
        if match_street:
            street = match_street.group(1)
            # Separa as cartas por espaço. Ex: "Qs 2h 9s" -> ["Qs", "2h", "9s"]
            cards_raw = match_street.group(2).split() 
            return StreetChangeEvent(street_name=street, cards=cards_raw)

        # 3. Tenta casar com Ações de Jogadores
        match_action = self.re_action.search(line)
        if match_action:
            player = match_action.group(1).strip()
            # Normalizamos o nome da ação para o domínio
            action = match_action.group(2).upper().replace("POSTS ", "")
            amount_str = match_action.group(3)
            amount = float(amount_str) if amount_str else 0.0
            
            return RawActionEvent(player=player, action_type=action, amount=amount)

        # Retorna None para todo o resto (chat, showdown, summary, etc), limpando o ruído.
        return None