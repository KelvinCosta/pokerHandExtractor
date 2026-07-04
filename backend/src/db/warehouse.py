import duckdb
from pathlib import Path

class DuckDBWarehouse:
    def __init__(self, silver_dir: str):
        self.silver_dir = Path(silver_dir)
        # O DuckDB roda em memoria por default, excelente para ler parquets "on the fly"
        self.conn = duckdb.connect(database=':memory:')
        
    def execute(self, query: str):
        """Executa uma query no DuckDB e retorna a relation para fetch"""
        return self.conn.execute(query)
        
    def get_silver_table(self) -> str:
        """
        Gera a string de acesso nativo aos arquivos da camada Silver.
        O DuckDB permite fazer: SELECT * FROM read_parquet('silver/*.parquet')
        """
        parquet_path = self.silver_dir / "hands_part_*.parquet"
        # Precisamos normalizar as barras para o DuckDB no Windows
        normalized_path = str(parquet_path).replace("\\", "/")
        return f"read_parquet('{normalized_path}')"
