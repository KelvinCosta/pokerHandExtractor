import argparse
import duckdb
import os
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import ValidationError
from dotenv import load_dotenv

from schemas import PlayerStats, TimeWindow

load_dotenv()

def extract_player_metrics(player_id: str, days_limit: int, stake_level: float, parquet_path: str = None) -> PlayerStats:
    """
    Conecta ao DuckDB, executa a query analítica sobre os arquivos Parquet 
    da Camada Silver e retorna as estatísticas validadas do jogador.
    """
    if not parquet_path or parquet_path == "hands_mock.parquet":
        silver_dir = Path(os.getenv("DATALAKE_SILVER", "datalake/silver"))
        parquet_path = str(silver_dir / "hands_part_*.parquet")
        
        # Verifica se o Datalake possui arquivos antes de acionar o motor
        if not list(silver_dir.glob("hands_part_*.parquet")):
            raise ValueError(f"O Datalake em '{silver_dir}' está vazio. Rode o extractor.py primeiro!")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_limit)
    
    # Query analítica real: Desempacota o array de structs 'actions' para calcular o comportamento.
    query = f"""
        WITH unnested_actions AS (
            SELECT 
                hand_id,
                date as hand_timestamp,
                stake_level,
                a.player,
                a.action_type,
                a.invested_amount,
                a.amount,
                a.street
            FROM read_parquet('{parquet_path}'), UNNEST(actions) as a
            WHERE stake_level = {stake_level}
              AND date >= '{start_date.isoformat()}'
        ),
        hand_metrics AS (
            SELECT 
                hand_id,
                MAX(stake_level) as stake_level,
                SUM(invested_amount) FILTER (WHERE player = '{player_id}' AND action_type NOT IN ('COLLECT', 'FOLD', 'CHECK')) as investido,
                SUM(amount) FILTER (WHERE player = '{player_id}' AND action_type = 'COLLECT') as coletado,
                COUNT(*) FILTER (WHERE player = '{player_id}' AND action_type IN ('BET', 'RAISE')) as agg_actions,
                COUNT(*) FILTER (WHERE player = '{player_id}' AND action_type = 'CALL') as call_actions,
                MAX(CASE WHEN player = '{player_id}' AND street = 'RIVER' THEN 1 ELSE 0 END) as went_to_showdown
            FROM unnested_actions
            GROUP BY hand_id
        )
        SELECT 
            '{player_id}' as player_id,
            CAST(COALESCE(SUM(COALESCE(coletado, 0) - COALESCE(investido, 0)) / {stake_level}, 0) AS DOUBLE) as profit_bb,
            CAST(COALESCE(SUM(agg_actions) / NULLIF(SUM(call_actions), 0), 0) AS DOUBLE) as aggressiveness_factor,
            CAST(COALESCE(AVG(went_to_showdown) * 100, 0) AS DOUBLE) as showdown_frequency,
            0 as consecutive_wins, -- Simplificado temporariamente
            0 as consecutive_losses -- Simplificado temporariamente
        FROM hand_metrics
    """
    
    try:
        # AQUI É REAL: Acionando o motor colunar do DuckDB
        result = duckdb.query(query).fetchone()
        
        # O DuckDB retorna (player_id, None, None) se não houver mãos agregadas
        if not result or result[1] is None:
            raise ValueError(f"Nenhum jogo encontrado para '{player_id}' no stake {stake_level}")

        stats = PlayerStats(
            player_id=result[0],
            profit_bb=result[1],
            aggressiveness_factor=result[2],
            showdown_frequency=result[3],
            consecutive_wins=result[4],
            consecutive_losses=result[5],
            time_window=TimeWindow(
                start_date=start_date,
                end_date=end_date,
                stake_level=stake_level
            )
        )
        return stats
        
    except duckdb.Error as e:
        raise RuntimeError(f"Erro interno no motor do DuckDB: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Extrai estatísticas determinísticas de Poker via DuckDB.")
    parser.add_argument("--player-id", type=str, required=True, help="ID do jogador a ser analisado.")
    parser.add_argument("--days", type=int, default=30, help="Janela de tempo em dias (padrão: 30).")
    parser.add_argument("--stake-level", type=float, required=True, help="Nível de aposta predominante (ex: 2.0 para NL2, 10.0 para NL10).")
    parser.add_argument("--out", type=str, default="current_state.json", help="Caminho do arquivo JSON de saída.")
    
    args = parser.parse_args()
    
    try:
        # Executa a extração matemática
        stats = extract_player_metrics(args.player_id, args.days, args.stake_level)
        
        # Exporta o resultado utilizando Pydantic para serialização nativa
        output_path = Path(args.out)
        with open(output_path, "w", encoding="utf-8") as file_out:
            file_out.write(stats.model_dump_json(indent=4))
            
        print(f"Sucesso: Estatísticas matemáticas do jogador '{args.player_id}' geradas e salvas em '{output_path}'.")
        
    except ValidationError as e:
        print(f"Falha Crítica - Quebra de Contrato de Dados (Pydantic):\n{e}")
    except Exception as e:
        print(f"Erro Inesperado:\n{e}")

if __name__ == "__main__":
    main()
