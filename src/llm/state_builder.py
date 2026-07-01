import polars as pl
from src.db.warehouse import DuckDBWarehouse

class SessionStateCalculator:
    def __init__(self, warehouse: DuckDBWarehouse, baseline_agressiveness: float = 0.45):
        self.warehouse = warehouse
        self.baseline_agressiveness = baseline_agressiveness

    def calculate_from_window(self, df: pl.DataFrame, hero_name: str, session_duration_minutes: float = 0.0, total_hands_played: int = 0) -> dict:
        """
        Sliding Window Calculator: Recebe um bloco (janela) de N mãos e calcula as métricas 
        comportamentais puras para essa janela específica.
        """
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
            
            # 1. Showdown Frequency
            if len(board_cards) == 5:
                showdown_count += 1
                
            # 2. Consecutive Losses
            if hero_won:
                consecutive_losses = 0
            else:
                consecutive_losses += 1
                
            hero_actions = [a for a in actions if a["player"] == hero_name]
            
            if hero_actions:
                max_invested = max([float(a["invested_amount"] or 0.0) for a in hero_actions] + [0.0])
                profit -= max_invested
                
                for act in hero_actions:
                    a_type = act["action_type"]
                    amount = float(act["amount"] or 0.0)
                    
                    if a_type == "COLLECT":
                        profit += amount
                        
                    if a_type in ("BET", "RAISE", "CALL", "CHECK", "FOLD"):
                        total_valid_actions += 1
                        if a_type in ("BET", "RAISE"):
                            agressive_actions += 1
                            
        agressiveness = 0.0
        if total_valid_actions > 0:
            agressiveness = agressive_actions / total_valid_actions
            
        return {
            "current_session_profit": round(profit, 2),
            "current_agressiveness": round(agressiveness, 2),
            "baseline_agressiveness": round(self.baseline_agressiveness, 2),
            "agressiveness_deviation": round(agressiveness - self.baseline_agressiveness, 2),
            "showdown_frequency": round(showdown_count / df.height, 2),
            "consecutive_losses": int(consecutive_losses),
            "session_duration_minutes": round(session_duration_minutes, 2),
            "total_hands_played": int(total_hands_played)
        }

    def get_current_state(self, hero_name: str, num_hands: int = 20) -> dict:
        table = self.warehouse.get_silver_table()
        
        # 1. Calcula estatísticas gerais da sessão inteira (considerando mãos das últimas 12 horas)
        session_query = f"""
            WITH LastHand AS (
                SELECT MAX(CAST(date AS TIMESTAMP)) as last_time FROM {table}
            )
            SELECT 
                COUNT(*) as total_hands,
                MIN(CAST(date AS TIMESTAMP)) as session_start,
                MAX(CAST(date AS TIMESTAMP)) as session_end
            FROM {table}, LastHand
            WHERE CAST(date AS TIMESTAMP) >= last_time - INTERVAL 12 HOUR
        """
        session_stats = self.warehouse.execute(session_query).fetchone()
        total_hands_played = session_stats[0] if session_stats else 0
        session_start = session_stats[1] if session_stats else None
        session_end = session_stats[2] if session_stats else None
        
        session_duration_minutes = 0.0
        if session_start and session_end:
            diff = session_end - session_start
            session_duration_minutes = diff.total_seconds() / 60.0

        # 2. Extrai as últimas num_hands agrupadas pela data para a Sliding Window
        query = f"""
            SELECT *
            FROM {table}
            ORDER BY date DESC
            LIMIT {num_hands}
        """
        # Contorno para OutOfMemoryException do DuckDB Arrow Allocator quando o Ollama consome muita RAM:
        # Convertendo via fetchall (tuplas nativas do Python) ao invés do .pl() direto
        result = self.warehouse.execute(query)
        columns = [desc[0] for desc in result.description]
        data = [dict(zip(columns, row)) for row in result.fetchall()]
        
        df = pl.DataFrame(data)
        
        if "date" in df.columns:
            df = df.sort("date")
        
        return self.calculate_from_window(df, hero_name, session_duration_minutes, total_hands_played)
