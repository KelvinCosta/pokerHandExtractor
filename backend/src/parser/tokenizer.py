import re
from pydantic import BaseModel, Field
from typing import List, Optional, Union

class HandStartEvent(BaseModel):
    hand_id: str
    timestamp: str = ""
    game_info: str = ""
    stake_level: float = 0.0

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

class PotSummaryEvent(BaseModel):
    total_pot: float = 0.0
    rake: float = 0.0
    jackpot: float = 0.0
    bingo: float = 0.0
    fortune: float = 0.0
    tax: float = 0.0

Token = Union[HandStartEvent, StreetChangeEvent, RawActionEvent, CardsRevealedEvent, PotSummaryEvent]

class GGPokerTokenizer:
    def __init__(self, hero_name: str = "Hero"):
        self.hero_name = hero_name
        self.re_hand_start = re.compile(r"^Poker Hand #([a-zA-Z0-9]+):\s*(.*?)\s*-\s*(\d{4}/\d{2}/\d{2}\s\d{2}:\d{2}:\d{2})")
        self.re_street = re.compile(r"^\*\*\* (FLOP|TURN|RIVER) \*\*\*\s+(.*)$")
        self.re_action = re.compile(r"^([^:]+): (folds|calls|raises|bets|checks|posts small blind|posts big blind|posts ante|posts the ante)(.*)")
        self.re_dealt = re.compile(r"^Dealt to ([^\[]+) \[([^\]]+)\]")
        self.re_shows = re.compile(r"^([^:]+): shows \[([^\]]+)\]")
        self.re_mucks = re.compile(r"^([^:]+): mucks \[([^\]]+)\]")
        self.re_collect = re.compile(r"^([^:]+?) collected \$?([0-9,]+(?:\.[0-9]+)?) from (?:main )?pot")

    def parse_line(self, line: str) -> Optional[Token]:
        line = line.strip()
        if not line:
            return None

        match_start = self.re_hand_start.search(line)
        if match_start:
            game_info_str = match_start.group(2).strip()
            stake_level = 0.0
            # Ex: "Hold'em No Limit ($0.05/$0.10)" ou "$1/$2"
            stake_match = re.search(r"\$([0-9.]+)/\$\$?([0-9.]+)", game_info_str)
            if not stake_match:
                stake_match = re.search(r"\$?([0-9.]+)/\$?([0-9.]+)", game_info_str)
            if stake_match:
                stake_level = float(stake_match.group(2))
            
            return HandStartEvent(hand_id=match_start.group(1), game_info=game_info_str, timestamp=match_start.group(3), stake_level=stake_level)

        match_street = self.re_street.search(line)
        if match_street:
            street = match_street.group(1)
            cards_raw = match_street.group(2).replace("[", "").replace("]", "").split()
            return StreetChangeEvent(street_name=street, cards=cards_raw)

        match_action = self.re_action.search(line)
        if match_action:
            player = match_action.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            raw_action = match_action.group(2).lower()

            if "posts" in raw_action:
                if "ante" in raw_action:
                    action = "ANTE"
                else:
                    action = "POST"
            else:
                action = raw_action.upper()
                if action.endswith("S") and action not in ["POSTS"]:
                    action = action[:-1]
            
            remainder = match_action.group(3)
            amount = 0.0
            if remainder:
                to_match = re.search(r"to \$?([0-9,]+(?:\.[0-9]+)?)", remainder)
                if to_match:
                    amount = float(to_match.group(1).replace(",", ""))
                else:
                    first_match = re.search(r"\$?([0-9,]+(?:\.[0-9]+)?)", remainder)
                    if first_match:
                        amount = float(first_match.group(1).replace(",", ""))
                        
            is_all_in = "and is all-in" in remainder.lower()

            return RawActionEvent(player=player, action_type=action, amount=amount, is_all_in=is_all_in)
            
        match_dealt = self.re_dealt.search(line)
        if match_dealt:
            player = match_dealt.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            return CardsRevealedEvent(player=player, cards=match_dealt.group(2))

        match_shows = self.re_shows.search(line)
        if match_shows:
            player = match_shows.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            return CardsRevealedEvent(player=player, cards=match_shows.group(2))

        match_mucks = self.re_mucks.search(line)
        if match_mucks:
            player = match_mucks.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            return CardsRevealedEvent(player=player, cards=match_mucks.group(2))
        
        match_collect = self.re_collect.search(line)
        if match_collect:
            player = match_collect.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            amount = float(match_collect.group(2).replace(",", ""))
            return RawActionEvent(player=player, action_type="COLLECT", amount=amount)

        # Trata as apostas não chamadas que são devolvidas (são um COLLECT técnico)
        match_uncalled = re.search(r"^Uncalled bet \(\$?([0-9,]+(?:\.[0-9]+)?)\) returned to ([^:]+)", line)
        if match_uncalled:
            amount = float(match_uncalled.group(1).replace(",", ""))
            player = match_uncalled.group(2).strip()
            if player == "Hero":
                player = self.hero_name
            return RawActionEvent(player=player, action_type="COLLECT", amount=amount)

        if line.startswith("Total pot "):
            match_summary = re.search(r"Total pot \$?([0-9,]+(?:\.[0-9]+)?)", line)
            if match_summary:
                total_pot = float(match_summary.group(1).replace(",", ""))
                
                def extract_val(label, txt):
                    m = re.search(f"{label} \\$?([0-9,]+(?:\\.[0-9]+)?)", txt)
                    return float(m.group(1).replace(",", "")) if m else 0.0
                    
                rake = extract_val("Rake", line)
                jackpot = extract_val("Jackpot", line)
                bingo = extract_val("Bingo", line)
                fortune = extract_val("Fortune", line)
                tax = extract_val("Tax", line)
                
                return PotSummaryEvent(total_pot=total_pot, rake=rake, jackpot=jackpot, bingo=bingo, fortune=fortune, tax=tax)

        return None

class TokenizerFactory:
    @staticmethod
    def get_tokenizer(platform: str, hero_name: str = "Hero"):
        platform_lower = platform.lower()
        if platform_lower in ["ggpoker", "gg"]:
            return GGPokerTokenizer(hero_name=hero_name)
        else:
            raise ValueError(f"Plataforma de poker não suportada: {platform}")