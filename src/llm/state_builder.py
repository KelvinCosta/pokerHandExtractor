import polars as pl
from src.db.warehouse import DuckDBWarehouse

class SessionStateCalculator:
    def __init__(self, warehouse: DuckDBWarehouse, baseline_agressiveness: float = 0.45):
        self.warehouse = warehouse
        self.baseline_agressiveness = baseline_agressiveness

    def get_current_state(self, hero_name: str, num_hands: int = 20) -> dict:
        table = self.warehouse.get_silver_table()
        
        # Extrair as últimas num_hands agrupadas pela data
        query = f"""
            SELECT *
            FROM {table}
            ORDER BY date DESC
            LIMIT {num_hands}
        """
        
        # Utilizamos DuckDB para ler e já retornar como Polars DataFrame
        df = self.warehouse.execute(query).pl()
        
        # Ordenamos de forma ascendente cronologicamente para cálculos em sequencia
        df = df.sort("date")
        
        if df.height == 0:
            return {
                "current_session_profit": 0.0,
                "agressiveness_deviation": 0.0,
                "showdown_frequency": 0.0,
                "consecutive_losses": 0
            }
            
        profit = 0.0
        agressive_actions = 0
        total_valid_actions = 0
        showdown_count = 0
        consecutive_losses = 0
        
        for row in df.iter_rows(named=True):
            hero_won = row["hero_ganhou"]
            board_cards = row["board_cards"] or []
            actions = row["actions"] or []
            
            # 1. Showdown Frequency (Simplificado pela presença das 5 comunitárias)
            if len(board_cards) == 5:
                showdown_count += 1
                
            # 2. Consecutive Losses
            if hero_won:
                consecutive_losses = 0
            else:
                consecutive_losses += 1
                
            # Filtra apenas ações do Hero
            hero_actions = [a for a in actions if a["player"] == hero_name]
            
            if hero_actions:
                # O investimento total da mão do hero é o pico do invested_amount nas ações
                # E garantimos que lide com nulos
                max_invested = max([float(a["invested_amount"] or 0.0) for a in hero_actions] + [0.0])
                profit -= max_invested
                
                for act in hero_actions:
                    a_type = act["action_type"]
                    amount = float(act["amount"] or 0.0)
                    
                    # 3. Lucro da Sessão (Somar tudo que ele recolheu)
                    if a_type == "COLLECT":
                        profit += amount
                        
                    # 4. Desvio de agressividade (Bets + Raises vs Ações Voluntárias)
                    if a_type in ("BET", "RAISE", "CALL", "CHECK", "FOLD"):
                        total_valid_actions += 1
                        if a_type in ("BET", "RAISE"):
                            agressive_actions += 1
                            
        agressiveness = 0.0
        if total_valid_actions > 0:
            agressiveness = agressive_actions / total_valid_actions
            
        return {
            "current_session_profit": float(profit),
            "agressiveness_deviation": float(agressiveness - self.baseline_agressiveness),
            "showdown_frequency": float(showdown_count / df.height),
            "consecutive_losses": int(consecutive_losses)
        }
