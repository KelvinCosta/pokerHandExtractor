import re
from typing import Optional
from src.parser.tokenizer import (
    HandStartEvent, ButtonInfoEvent, SeatInfoEvent, StreetChangeEvent,
    RawActionEvent, CardsRevealedEvent, PotSummaryEvent, EVEvent, Token
)

class PartyPokerTokenizer:
    def __init__(self, hero_name: str = "Hero"):
        self.hero_name = hero_name
        
        # Ex: ***** Hand History for Game 123456 ***** 
        # Followed by stakes/time info which varies slightly, but typically starts with Game #...
        self.re_hand_start = re.compile(r"^\*\*\*\*\* Hand History for Game ([0-9]+) \*\*\*\*\*")
        
        # We also need a regex to grab stakes on subsequent lines if necessary, 
        # but PartyPoker often formats like: $1/$2 USD NL Texas Hold'em - Sunday, October 01, 10:00:00 ET 2026
        self.re_game_info = re.compile(r"^\$([0-9,.]+)/\$([0-9,.]+) (.*) - (.*)")
        
        # Ex: Seat 1 is the button
        self.re_button = re.compile(r"^Seat (\d+) is the button")
        
        # Ex: Seat 1: Player ( $1,000 USD )
        self.re_seat = re.compile(r"^Seat (\d+): (.*?) \( \$?([0-9,.]+).*?\)")
        
        # Ex: ** Dealing Flop ** [ Ah, Kd, Qc ]
        self.re_street = re.compile(r"^\*\* Dealing (Flop|Turn|River) \*\*\s+\[(.*?)\]")
        
        # Actions: Player folds / Player calls / Player raises / Player bets / Player is all-In  [ $100 USD ]
        self.re_action = re.compile(r"^([^:]+)\s+(folds|calls|raises|bets|is all-In|checks|posts small blind|posts big blind)(?:\s+\[ \$?([0-9,.]+) )?")
        
        # Ex: Dealt to Hero [ Ah, Kd ]
        self.re_dealt = re.compile(r"^Dealt to ([^\[]+) \[\s*([^\]]+)\s*\]")
        
        # Ex: Player shows [ Ah, Kd ]
        self.re_shows = re.compile(r"^([^:]+) shows \[\s*([^\]]+)\s*\]")
        self.re_mucks = re.compile(r"^([^:]+) mucks \[\s*([^\]]+)\s*\]")
        
        # Ex: Player wins $1,000 from the main pot
        self.re_collect = re.compile(r"^([^:]+) wins \$?([0-9,.]+)")

        self.current_hand_id = None
        
    def parse_line(self, line: str) -> Optional[Token]:
        line = line.strip()
        if not line:
            return None

        match_start = self.re_hand_start.search(line)
        if match_start:
            self.current_hand_id = match_start.group(1)
            # Retorna parcial, as stakes podem vir nas próximas linhas em algumas variantes
            return HandStartEvent(hand_id=self.current_hand_id, game_info="PartyPoker", timestamp="", stake_level=0.0)
            
        match_info = self.re_game_info.search(line)
        if match_info and self.current_hand_id:
            # Se for a linha com detalhes, poderíamos armazenar estado, mas no modelo atual 
            # não temos um update event de stake fácil sem complicar o FSM. 
            pass

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
            street = match_street.group(1).upper()
            # PartyPoker cards are separated by commas usually [ Ah, Kd, Qc ]
            cards_raw = [c.strip() for c in match_street.group(2).replace(",", " ").split() if c.strip()]
            return StreetChangeEvent(street_name=street, cards=cards_raw)

        match_action = self.re_action.search(line)
        if match_action:
            player = match_action.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            raw_action = match_action.group(2).lower()

            if "posts" in raw_action:
                action = "POST"
            elif raw_action == "is all-in":
                action = "RAISE" # Ou BET/CALL dependendo do contexto, mas vamos mapear p/ RAISE/ALL_IN
            else:
                action = raw_action.upper()
                if action.endswith("S") and action not in ["POSTS"]:
                    action = action[:-1]
            
            amount = 0.0
            if match_action.group(3):
                amount = float(match_action.group(3).replace(",", ""))
                        
            is_all_in = "all-in" in raw_action

            return RawActionEvent(player=player, action_type=action, amount=amount, is_all_in=is_all_in)
            
        match_dealt = self.re_dealt.search(line)
        if match_dealt:
            player = match_dealt.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            return CardsRevealedEvent(player=player, cards=match_dealt.group(2).replace(",", ""), is_dealt=True)

        match_shows = self.re_shows.search(line)
        if match_shows:
            player = match_shows.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            return CardsRevealedEvent(player=player, cards=match_shows.group(2).replace(",", ""))

        match_mucks = self.re_mucks.search(line)
        if match_mucks:
            player = match_mucks.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            return CardsRevealedEvent(player=player, cards=match_mucks.group(2).replace(",", ""))
        
        match_collect = self.re_collect.search(line)
        if match_collect:
            player = match_collect.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            amount = float(match_collect.group(2).replace(",", ""))
            return RawActionEvent(player=player, action_type="COLLECT", amount=amount)

        return None
