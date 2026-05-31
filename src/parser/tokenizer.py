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

class CardsRevealedEvent(BaseModel):
    player: str
    cards: str

Token = Union[HandStartEvent, StreetChangeEvent, RawActionEvent]

class GGPokerTokenizer:
    """
    Lê linhas de texto bruto e tenta convertê-las em Eventos Pydantic tipados.
    Atua como Anti-Corruption Layer (ACL).
    """
    def __init__(self):
        self.re_hand_start = re.compile(r"^Poker Hand #([a-zA-Z0-9]+):")
        self.re_street = re.compile(r"^\*\*\* (FLOP|TURN|RIVER) \*\*\*.*\[([^\]]+)\]\s*$")
        self.re_action = self.re_action = re.compile(r"^([^:]+): (folds|calls|raises|bets|checks|posts small blind|posts big blind)(?:.*\$([0-9\.]+))?")
        self.re_dealt = re.compile(r"^Dealt to ([^\[]+) \[([^\]]+)\]")
        self.re_shows = re.compile(r"^([^:]+): shows \[([^\]]+)\]")
        self.re_mucks = re.compile(r"^([^:]+): mucks \[([^\]]+)\]")

    def parse_line(self, line: str) -> Optional[Token]:
        line = line.strip()
        if not line:
            return None

        match_start = self.re_hand_start.search(line)
        if match_start:
            return HandStartEvent(hand_id=match_start.group(1))

        match_street = self.re_street.search(line)
        if match_street:
            street = match_street.group(1)
            cards_raw = match_street.group(2).split() 
            return StreetChangeEvent(street_name=street, cards=cards_raw)

        match_action = self.re_action.search(line)
        if match_action:
            player = match_action.group(1).strip()
            action = match_action.group(2).upper().replace("POSTS ", "")
            amount_str = match_action.group(3)
            amount = float(amount_str) if amount_str else 0.0
            
            return RawActionEvent(player=player, action_type=action, amount=amount)
        match_dealt = self.re_dealt.search(line)
        if match_dealt:
            return CardsRevealedEvent(player=match_dealt.group(1).strip(), cards=match_dealt.group(2))

        match_shows = self.re_shows.search(line)
        if match_shows:
            return CardsRevealedEvent(player=match_shows.group(1).strip(), cards=match_shows.group(2))

        match_mucks = self.re_mucks.search(line)
        if match_mucks:
            return CardsRevealedEvent(player=match_mucks.group(1).strip(), cards=match_mucks.group(2))
        return None