import re
from pydantic import BaseModel, Field
from typing import List, Optional, Union

class HandStartEvent(BaseModel):
    hand_id: str
    timestamp: str = ""

class StreetChangeEvent(BaseModel):
    street_name: str 
    cards: List[str]

class RawActionEvent(BaseModel):
    player: str
    action_type: str
    amount: float = Field(default=0.0, ge=0.0)

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
    def __init__(self):
        self.re_hand_start = re.compile(r"^Poker Hand #(RC[0-9]+):.* - (\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")
        self.re_street = re.compile(r"^\*\*\* (FLOP|TURN|RIVER) \*\*\*\s+(.*)$")
        self.re_action = re.compile(r"^([^:]+): (folds|calls|raises|bets|checks|posts small blind|posts big blind|posts ante)(.*)")
        self.re_dealt = re.compile(r"^Dealt to ([^\[]+) \[([^\]]+)\]")
        self.re_shows = re.compile(r"^([^:]+): shows \[([^\]]+)\]")
        self.re_mucks = re.compile(r"^([^:]+): mucks \[([^\]]+)\]")
        self.re_collect = re.compile(r"^([^:]+?) collected \$?([0-9]+(?:\.[0-9]+)?) from (?:main )?pot")

    def parse_line(self, line: str) -> Optional[Token]:
        line = line.strip()
        if not line:
            return None

        match_start = self.re_hand_start.search(line)
        if match_start:
            return HandStartEvent(hand_id=match_start.group(1), timestamp=match_start.group(2))

        match_street = self.re_street.search(line)
        if match_street:
            street = match_street.group(1)
            cards_raw = match_street.group(2).replace("[", "").replace("]", "").split()
            return StreetChangeEvent(street_name=street, cards=cards_raw)

        match_action = self.re_action.search(line)
        if match_action:
            player = match_action.group(1).strip()
            raw_action = match_action.group(2).lower()

            if "posts" in raw_action:
                action = "POST"
            else:
                action = raw_action.upper()
                if action.endswith("S") and action not in ["POSTS"]:
                    action = action[:-1]
            
            remainder = match_action.group(3)
            amount = 0.0
            if remainder:
                to_match = re.search(r"to \$?([0-9]+(?:\.[0-9]+)?)", remainder)
                if to_match:
                    amount = float(to_match.group(1))
                else:
                    first_match = re.search(r"\$?([0-9]+(?:\.[0-9]+)?)", remainder)
                    if first_match:
                        amount = float(first_match.group(1))

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
        
        match_collect = self.re_collect.search(line)
        if match_collect:
            player = match_collect.group(1).strip()
            amount = float(match_collect.group(2))
            return RawActionEvent(player=player, action_type="COLLECT", amount=amount)

        if line.startswith("Total pot $"):
            match_summary = re.search(r"Total pot \$([0-9.]+)", line)
            if match_summary:
                total_pot = float(match_summary.group(1))
                rake = float(re.search(r"Rake \$([0-9.]+)", line).group(1)) if "Rake $" in line else 0.0
                jackpot = float(re.search(r"Jackpot \$([0-9.]+)", line).group(1)) if "Jackpot $" in line else 0.0
                bingo = float(re.search(r"Bingo \$([0-9.]+)", line).group(1)) if "Bingo $" in line else 0.0
                fortune = float(re.search(r"Fortune \$([0-9.]+)", line).group(1)) if "Fortune $" in line else 0.0
                tax = float(re.search(r"Tax \$([0-9.]+)", line).group(1)) if "Tax $" in line else 0.0
                return PotSummaryEvent(total_pot=total_pot, rake=rake, jackpot=jackpot, bingo=bingo, fortune=fortune, tax=tax)

        return None