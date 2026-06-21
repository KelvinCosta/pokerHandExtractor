import re
import os
from typing import Optional, Dict
from pydantic import BaseModel

class TournamentSummary(BaseModel):
    tournament_id: str
    buy_in: float
    prize: float
    source_file: str

class SummaryParser:
    def __init__(self):
        self.re_tournament = re.compile(r"^Tournament #([0-9]+),")
        self.re_buyin = re.compile(r"^Buy-in:\s*\$([0-9.]+)")
        self.re_free = re.compile(r"^Buy-in:\s*Free", re.IGNORECASE)
        self.re_prize = re.compile(r"^You received a total of \$([0-9.]+)")

    def is_summary_file(self, filepath: str) -> bool:
        """Verifica se o arquivo é um Tournament Summary (geralmente bem pequeno)"""
        try:
            # Se o arquivo for muito grande, não é um summary
            if os.path.getsize(filepath) > 5000:
                return False
                
            with open(filepath, "r", encoding="utf-8-sig") as f:
                first_line = f.readline().strip()
                # O summary sempre começa com "Tournament #"
                return first_line.startswith("Tournament #")
        except Exception:
            return False

    def parse_file(self, filepath: str) -> Optional[TournamentSummary]:
        try:
            t_id = None
            buy_in = 0.0
            prize = 0.0
            
            with open(filepath, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    match_t = self.re_tournament.search(line)
                    if match_t:
                        t_id = match_t.group(1)
                        continue
                        
                    match_buyin = self.re_buyin.search(line)
                    if match_buyin:
                        buy_in = float(match_buyin.group(1))
                        continue
                    elif self.re_free.search(line):
                        buy_in = 0.0
                        continue
                        
                    match_prize = self.re_prize.search(line)
                    if match_prize:
                        prize = float(match_prize.group(1))
                        continue

            if t_id:
                # Caso a string indique que ele terminou, mas não pegou prêmio (0.0 padrão)
                return TournamentSummary(
                    tournament_id=t_id,
                    buy_in=buy_in,
                    prize=prize,
                    source_file=os.path.basename(filepath)
                )
                
            return None
            
        except Exception as e:
            print(f"Erro ao parsear summary {filepath}: {e}")
            return None
