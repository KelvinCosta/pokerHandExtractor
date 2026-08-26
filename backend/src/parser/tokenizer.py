import re
from pydantic import BaseModel, Field
from typing import List, Optional, Union

class HandStartEvent(BaseModel):
    hand_id: str
    timestamp: str = ""
    game_info: str = ""
    stake_level: float = 0.0

class ButtonInfoEvent(BaseModel):
    button_seat: int

class SeatInfoEvent(BaseModel):
    seat: int
    player: str
    starting_stack: float

class StreetChangeEvent(BaseModel):
    street_name: str 
    cards: List[str]

class RawActionEvent(BaseModel):
    player: str
    action_type: str
    amount: float = Field(default=0.0, ge=0.0)
    is_all_in: bool = False

class CardsRevealedEvent(BaseModel):
    player: str
    cards: str
    is_dealt: bool = False

class PotSummaryEvent(BaseModel):
    total_pot: float = 0.0
    rake: float = 0.0
    jackpot: float = 0.0
    bingo: float = 0.0
    fortune: float = 0.0
    tax: float = 0.0

class EVEvent(BaseModel):
    player: str
    ev_amount: float = 0.0

Token = Union[HandStartEvent, ButtonInfoEvent, SeatInfoEvent, StreetChangeEvent, RawActionEvent, CardsRevealedEvent, PotSummaryEvent, EVEvent]

class TokenizerFactory:
    @staticmethod
    def get_tokenizer(platform: str, hero_name: str = "Hero"):
        platform_lower = platform.lower()
        if platform_lower in ["ggpoker", "gg"]:
            from src.parser.tokenizers.ggpoker import GGPokerTokenizer
            return GGPokerTokenizer(hero_name=hero_name)
        elif platform_lower in ["pokerstars", "ps"]:
            from src.parser.tokenizers.pokerstars import PokerStarsTokenizer
            return PokerStarsTokenizer(hero_name=hero_name)
        elif platform_lower in ["partypoker", "party"]:
            from src.parser.tokenizers.partypoker import PartyPokerTokenizer
            return PartyPokerTokenizer(hero_name=hero_name)
        elif platform_lower in ["ipoker", "ip"]:
            from src.parser.tokenizers.ipoker import IPokerTokenizer
            return IPokerTokenizer(hero_name=hero_name)
        else:
            raise ValueError(f"Plataforma de poker não suportada: {platform}")