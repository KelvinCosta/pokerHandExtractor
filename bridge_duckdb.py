import argparse
import duckdb
import os
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import ValidationError
from dotenv import load_dotenv

from schemas import PlayerStats, TimeWindow

load_dotenv()

def extract_player_metrics(player_id: str, days_limit: int, stake_level: float, game_type: str, parquet_path: str = None) -> PlayerStats:
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
    start_date_str = start_date.strftime('%Y/%m/%d %H:%M:%S')
    
    # Query analítica real: Desempacota o array de structs 'actions' para calcular o comportamento.
    query = f"""
        -- TODO: Métricas Futuras - Para extrair 'C-Bet' e 'Fold to 3-Bet' precisaremos fazer self-joins 
        -- rastreando o agressor na street anterior. 
        -- Para extrair 'Lucro por Posição', o ETL precisará mapear o Seat do Hero no JSON.
        WITH raw_unnest AS (
            SELECT 
                hand_id,
                date as hand_timestamp,
                stake_level,
                hero_ganhou,
                UNNEST(actions) as act
            FROM read_parquet('{parquet_path}')
            WHERE ABS(stake_level - {stake_level}) < 0.001
              AND game_type = '{game_type}'
              AND date >= '{start_date_str}'
        ),
        unnested_actions AS (
            SELECT
                hand_id,
                hand_timestamp,
                stake_level,
                hero_ganhou,
                act.player as player,
                act.action_type as action_type,
                act.invested_amount as invested_amount,
                act.amount as amount,
                act.street as street,
                act.is_all_in as is_all_in
            FROM raw_unnest
        ),
        hand_metrics AS (
            SELECT 
                hand_id,
                MAX(stake_level) as stake_level,
                MAX(CAST(hero_ganhou AS INTEGER)) as hero_ganhou,
                MAX(hand_timestamp) as hand_timestamp,
                SUM(invested_amount) FILTER (WHERE player = '{player_id}' AND action_type NOT IN ('COLLECT', 'FOLD', 'CHECK')) as investido,
                SUM(amount) FILTER (WHERE player = '{player_id}' AND action_type = 'COLLECT') as coletado,
                COUNT(*) FILTER (WHERE player = '{player_id}' AND action_type IN ('BET', 'RAISE')) as agg_actions,
                COUNT(*) FILTER (WHERE player = '{player_id}' AND action_type = 'CALL') as call_actions,
                MAX(CASE WHEN player = '{player_id}' AND street = 'RIVER' THEN 1 ELSE 0 END) as went_to_showdown,
                MAX(CASE WHEN player = '{player_id}' AND street = 'PRE_FLOP' AND action_type IN ('BET', 'RAISE', 'CALL') THEN 1 ELSE 0 END) as vpip_flag,
                MAX(CASE WHEN player = '{player_id}' AND street = 'PRE_FLOP' AND action_type IN ('BET', 'RAISE') THEN 1 ELSE 0 END) as pfr_flag,
                MAX(CASE WHEN player = '{player_id}' AND is_all_in = TRUE THEN 1 ELSE 0 END) as all_in_flag,
                MAX(CASE WHEN player = '{player_id}' AND street = 'FLOP' THEN 1 ELSE 0 END) as saw_flop_flag
            FROM unnested_actions
            GROUP BY hand_id
        ),
        streak_calc AS (
            SELECT
                hand_id,
                hand_timestamp,
                investido,
                coletado,
                agg_actions,
                call_actions,
                went_to_showdown,
                vpip_flag,
                pfr_flag,
                all_in_flag,
                saw_flop_flag,
                (COALESCE(coletado, 0) - COALESCE(investido, 0)) as profit,
                CASE WHEN (COALESCE(coletado, 0) - COALESCE(investido, 0)) > 0 THEN 1 ELSE 0 END as is_win,
                CASE WHEN (COALESCE(coletado, 0) - COALESCE(investido, 0)) < 0 THEN 1 ELSE 0 END as is_loss,
                ROW_NUMBER() OVER(ORDER BY hand_timestamp) as rn_total,
                ROW_NUMBER() OVER(PARTITION BY CASE WHEN (COALESCE(coletado, 0) - COALESCE(investido, 0)) > 0 THEN 1 ELSE 0 END ORDER BY hand_timestamp) as rn_win,
                ROW_NUMBER() OVER(PARTITION BY CASE WHEN (COALESCE(coletado, 0) - COALESCE(investido, 0)) < 0 THEN 1 ELSE 0 END ORDER BY hand_timestamp) as rn_loss
            FROM hand_metrics
        ),
        streak_groups AS (
            SELECT
                *,
                (rn_total - rn_win) as win_streak_id,
                (rn_total - rn_loss) as loss_streak_id
            FROM streak_calc
        )
        SELECT 
            '{player_id}' as player_id,
            COUNT(*) as hands_played,
            ROUND(CAST(COALESCE((SUM(profit) / {stake_level} / NULLIF(COUNT(*), 0)) * 100, 0) AS DOUBLE), 2) as win_rate_bb100,
            ROUND(CAST(COALESCE(AVG(vpip_flag) * 100, 0) AS DOUBLE), 2) as vpip,
            ROUND(CAST(COALESCE(AVG(pfr_flag) * 100, 0) AS DOUBLE), 2) as pfr,
            ROUND(CAST(COALESCE(AVG(all_in_flag) * 100, 0) AS DOUBLE), 2) as all_in_freq,
            ROUND(CAST(COALESCE(SUM(CASE WHEN went_to_showdown = 1 AND profit > 0 THEN 1 ELSE 0 END) / CAST(NULLIF(SUM(went_to_showdown), 0) AS DOUBLE) * 100, 0) AS DOUBLE), 2) as wsd,
            ROUND(CAST(COALESCE(SUM(CASE WHEN saw_flop_flag = 1 AND profit > 0 THEN 1 ELSE 0 END) / CAST(NULLIF(SUM(saw_flop_flag), 0) AS DOUBLE) * 100, 0) AS DOUBLE), 2) as wwsf,
            ROUND(CAST(COALESCE(SUM(profit) / {stake_level}, 0) AS DOUBLE), 2) as profit_bb,
            ROUND(CAST(COALESCE(SUM(agg_actions) / NULLIF(SUM(call_actions), 0), 0) AS DOUBLE), 2) as aggressiveness_factor,
            ROUND(CAST(COALESCE(AVG(went_to_showdown) * 100, 0) AS DOUBLE), 2) as showdown_frequency,
            CAST(COALESCE((SELECT MAX(win_len) FROM (SELECT SUM(is_win) as win_len FROM streak_groups WHERE is_win = 1 GROUP BY win_streak_id)), 0) AS INTEGER) as consecutive_wins,
            CAST(COALESCE((SELECT MAX(loss_len) FROM (SELECT SUM(is_loss) as loss_len FROM streak_groups WHERE is_loss = 1 GROUP BY loss_streak_id)), 0) AS INTEGER) as consecutive_losses
        FROM streak_groups
    """
    
    try:
        # AQUI É REAL: Acionando o motor colunar do DuckDB
        result = duckdb.query(query).fetchone()
        
        # O DuckDB retorna (player_id, None, None) se não houver mãos agregadas
        if not result or result[8] is None:
            available_games = duckdb.query(f"SELECT DISTINCT game_type FROM read_parquet('{parquet_path}')").fetchall()
            options_str = ", ".join(f"'{row[0]}'" for row in available_games if row[0])
            raise ValueError(f"Nenhum jogo encontrado para '{player_id}' no stake {stake_level} com game_type '{game_type}'.\nOpções válidas na sua base: {options_str}")

        stats = PlayerStats(
            player_id=result[0],
            hands_played=result[1],
            win_rate_bb100=result[2],
            vpip=result[3],
            pfr=result[4],
            all_in_freq=result[5],
            wsd=result[6],
            wwsf=result[7],
            profit_bb=result[8],
            aggressiveness_factor=result[9],
            showdown_frequency=result[10],
            consecutive_wins=result[11],
            consecutive_losses=result[12],
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
    parser.add_argument("--stake-level", type=float, required=True, help="Nível de aposta predominante (ex: 0.02 para NL2, 0.10 para NL10).")
    parser.add_argument("--game-type", type=str, required=True, help="Tipo de jogo a ser auditado (ex: 'Regular Cash', 'Rush & Cash', 'Tournament').")
    parser.add_argument("--out", type=str, default="current_state.json", help="Caminho do arquivo JSON de saída.")
    
    args = parser.parse_args()
    
    try:
        # Executa a extração matemática
        stats = extract_player_metrics(args.player_id, args.days, args.stake_level, args.game_type)
        
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
