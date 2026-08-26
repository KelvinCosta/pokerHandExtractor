import re
from typing import Optional
from src.parser.tokenizer import (
    HandStartEvent, ButtonInfoEvent, SeatInfoEvent, StreetChangeEvent,
    RawActionEvent, CardsRevealedEvent, PotSummaryEvent, EVEvent, Token
)

class PokerStarsTokenizer:
    def __init__(self, hero_name: str = "Hero"):
        self.hero_name = hero_name
        # Ex: PokerStars Hand #215904000: Hold'em No Limit ($0.01/$0.02 USD) - 2026/06/19 10:00:00 ET
        self.re_hand_start = re.compile(r"^PokerStars [^#]+ #([0-9]+):\s*(.*?)\s*-\s*(\d{4}/\d{2}/\d{2}\s\d{2}:\d{2}:\d{2})")
        
        # Ex: Table 'A' 6-max Seat #1 is the button
        self.re_button = re.compile(r"Seat #(\d+) is the button")
        
        # Ex: Seat 1: Player (1000 in chips)
        self.re_seat = re.compile(r"^Seat (\d+): (.*?) \(\$?([0-9,.]+)(?: in chips)?\)")
        
        # Ex: *** FLOP *** [Ah Kd Qc]
        self.re_street = re.compile(r"^\*\*\* (FLOP|TURN|RIVER) \*\*\*\s+.*?(?:\[([^\]]+)\])$")
        
        # Actions
        self.re_action = re.compile(r"^([^:]+): (folds|calls|raises|bets|checks|posts small blind|posts big blind|posts ante|posts the ante)(.*)")
        
        # Ex: Dealt to Hero [Ah Kd]
        self.re_dealt = re.compile(r"^Dealt to ([^\[]+) \[([^\]]+)\]")
        
        # Ex: Player: shows [Ah Kd]
        self.re_shows = re.compile(r"^([^:]+): shows \[([^\]]+)\]")
        self.re_mucks = re.compile(r"^([^:]+): mucks \[([^\]]+)\]")
        
        # Ex: Player collected 1000 from pot
        self.re_collect = re.compile(r"^([^:]+?) collected \$?([0-9,]+(?:\.[0-9]+)?) from (?:main )?pot")
        
        # Ex: Total pot $10 | Rake $0.50
        self.re_summary = re.compile(r"^Total pot \$?([0-9,]+(?:\.[0-9]+)?)")

    def parse_line(self, line: str) -> Optional[Token]:
        line = line.strip()
        if not line:
            return None

        match_start = self.re_hand_start.search(line)
        if match_start:
            game_info_str = match_start.group(2).strip()
            stake_level = 0.0
            stake_match = re.search(r"\$([0-9,.]+)/\$\$?([0-9,.]+)", game_info_str)
            if not stake_match:
                stake_match = re.search(r"\$?([0-9,.]+)/\$?([0-9,.]+)", game_info_str)
            if stake_match:
                stake_level = float(stake_match.group(2).replace(",", ""))
            
            return HandStartEvent(hand_id=match_start.group(1), game_info=game_info_str, timestamp=match_start.group(3), stake_level=stake_level)

        match_button = self.re_button.search(line)
        if match_button:
            return ButtonInfoEvent(button_seat=int(match_button.group(1)))
            
        match_seat = self.re_seat.search(line)
        if match_seat:
            player_name = match_seat.group(2).strip()
            if player_name == "Hero":
                player_name = self.hero_name
            stack = float(match_seat.group(3).replace(",", ""))
            return SeatInfoEvent(seat=int(match_seat.group(1)), player=player_name, starting_stack=stack)

        match_street = self.re_street.search(line)
        if match_street:
            street = match_street.group(1)
            cards_raw = match_street.group(2).split() if match_street.group(2) else []
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
            return CardsRevealedEvent(player=player, cards=match_dealt.group(2), is_dealt=True)

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

        match_uncalled = re.search(r"^Uncalled bet \(\$?([0-9,]+(?:\.[0-9]+)?)\) returned to ([^:]+)", line)
        if match_uncalled:
            amount = float(match_uncalled.group(1).replace(",", ""))
            player = match_uncalled.group(2).strip()
            if player == "Hero":
                player = self.hero_name
            return RawActionEvent(player=player, action_type="COLLECT", amount=amount)

        if line.startswith("Total pot "):
            match_summary = self.re_summary.search(line)
            if match_summary:
                total_pot = float(match_summary.group(1).replace(",", ""))
                
                def extract_val(label, txt):
                    m = re.search(f"{label} \\$?([0-9,]+(?:\\.[0-9]+)?)", txt)
                    return float(m.group(1).replace(",", "")) if m else 0.0
                    
                rake = extract_val("Rake", line)
                return PotSummaryEvent(total_pot=total_pot, rake=rake)

        return None
