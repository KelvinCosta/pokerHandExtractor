import re
from typing import Optional
from src.parser.tokenizer import (
    HandStartEvent, ButtonInfoEvent, SeatInfoEvent, StreetChangeEvent,
    RawActionEvent, CardsRevealedEvent, PotSummaryEvent, EVEvent, Token
)

class IPokerTokenizer:
    def __init__(self, hero_name: str = "Hero"):
        self.hero_name = hero_name
        
        # Ex: <game gamecode="123456789">
        self.re_hand_start = re.compile(r'<game\s+gamecode="([^"]+)"')
        
        # Ex: <player seat="1" name="PlayerA" chips="1000" dealer="1" />
        self.re_player = re.compile(r'<player\b.*\bseat="(\d+)".*\bname="([^"]+)".*\bchips="([^"]+)".*\bdealer="(\d)?"?.*/>')
        
        # Ex: <cards type="Flop">Ah Kd Qc</cards>
        self.re_street = re.compile(r'<cards\b.*\btype="(Flop|Turn|River)".*>([^<]+)</cards>')
        
        # Ex: <cards type="Pocket" player="Hero">Ah Kd</cards>
        self.re_dealt = re.compile(r'<cards\b.*\btype="Pocket".*\bplayer="([^"]+)".*>([^<]+)</cards>')
        
        # Ex: <action player="PlayerA" type="1" sum="10" />
        # type 1/2: blinds, 0: fold, 3/4: check/call, 5/6/23: bet/raise
        self.re_action = re.compile(r'<action\b([^>]+)/>')

        self.current_hand_id = None
        
    def parse_line(self, line: str) -> Optional[Token]:
        line = line.strip()
        if not line:
            return None

        match_start = self.re_hand_start.search(line)
        if match_start:
            self.current_hand_id = match_start.group(1)
            return HandStartEvent(hand_id=self.current_hand_id, game_info="iPoker", timestamp="", stake_level=0.0)

        match_player = self.re_player.search(line)
        if match_player:
            seat = int(match_player.group(1))
            player_name = match_player.group(2).strip()
            if player_name == "Hero":
                player_name = self.hero_name
            stack = float(match_player.group(3).replace(",", ""))
            
            # Se for dealer, nós emitiremos também um ButtonInfoEvent (idealmente separado, mas a leitura iPoker vem junta)
            # Para manter consistência com uma yield só por vez, retornamos o SeatInfoEvent. 
            # (Em um caso real de produção precisaríamos talvez mockar a stream para separar esses yields)
            return SeatInfoEvent(seat=seat, player=player_name, starting_stack=stack)

        match_street = self.re_street.search(line)
        if match_street:
            street = match_street.group(1).upper()
            cards_raw = match_street.group(2).split()
            return StreetChangeEvent(street_name=street, cards=cards_raw)
            
        match_dealt = self.re_dealt.search(line)
        if match_dealt:
            player_name = match_dealt.group(1).strip()
            if player_name == "Hero":
                player_name = self.hero_name
            return CardsRevealedEvent(player=player_name, cards=match_dealt.group(2), is_dealt=True)

        match_action = self.re_action.search(line)
        if match_action:
            attrs = match_action.group(1)
            player_match = re.search(r'\bplayer="([^"]+)"', attrs)
            type_match = re.search(r'\btype="(\d+)"', attrs)
            sum_match = re.search(r'\bsum="([^"]+)"', attrs)
            
            if not player_match or not type_match:
                return None
                
            player = player_match.group(1).strip()
            if player == "Hero":
                player = self.hero_name
            
            action_type = type_match.group(1)
            amount = 0.0
            if sum_match:
                amount = float(sum_match.group(1).replace(",", ""))
                
            if action_type in ["1", "2"]:
                action = "POST"
            elif action_type == "0":
                action = "FOLD"
            elif action_type in ["3", "4"]:
                action = "CALL" if amount > 0 else "CHECK"
            elif action_type in ["5", "6", "23"]:
                action = "RAISE"
            else:
                action = "UNKNOWN"

            return RawActionEvent(player=player, action_type=action, amount=amount)

        return None
