import argparse
import duckdb
import os
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import ValidationError
from dotenv import load_dotenv

from schemas import PlayerStats, TimeWindow, GlobalStats, BehavioralTriggers

load_dotenv()

def parse_args():
    parser = argparse.ArgumentParser(description="Extrai estatísticas determinísticas de Poker via DuckDB.")
    parser.add_argument("--player-id", required=True, help="ID do jogador a ser analisado.")
    parser.add_argument("--days", type=int, default=30, help="Janela de tempo em dias (padrão: 30).")
    parser.add_argument("--stake-level", type=float, required=True, help="Nível de aposta predominante (ex: 0.02 para NL2, 0.10 para NL10).")
    parser.add_argument("--game-type", type=str, required=True, help="Tipo de jogo a ser auditado (ex: 'Regular Cash', 'Rush & Cash', 'Tournament').")
    parser.add_argument("--out", type=str, default="current_state.json", help="Caminho do arquivo JSON de saída.")
    return parser.parse_args()

def extract_player_metrics(parquet_path: str, player_id: str, days_limit: int, stake_level: float, game_type: str) -> PlayerStats:
    """Lê os Parquets da camada Silver e agrega via SQL usando DuckDB."""
    
    if not Path(parquet_path).exists():
        silver_dir = Path(parquet_path).parent
        if not silver_dir.exists():
            raise ValueError(f"O caminho base para o Datalake não existe: {silver_dir}")
            
        if not list(silver_dir.glob("hands_part_*.parquet")):
            raise ValueError(f"O Datalake em '{silver_dir}' está vazio. Rode o extractor.py primeiro!")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_limit)
    start_date_str = start_date.strftime('%Y/%m/%d %H:%M:%S')
    
    query = f"""
        -- TODO: Extrair EV do arquivo .txt na fase de ETL (extractor/loader) e persistir no Parquet para substituir o mock (0.0) de ev_bb100 e ev_diff_bb
        -- TODO: Métricas Futuras - Para extrair 'C-Bet' e 'Fold to 3-Bet' precisaremos fazer self-joins 
        -- rastreando o agressor na street anterior. 
        -- Para extrair 'Lucro por Posição', o ETL precisará mapear o Seat do Hero no JSON.
        WITH raw_unnest AS (
            SELECT 
                hand_id,
                date as hand_timestamp,
                stake_level,
                hero_ganhou,
                hero_expected_value_bb,
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
                hero_expected_value_bb,
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
                MAX(hand_timestamp) as hand_timestamp,
                MAX(hero_expected_value_bb) as hero_expected_value_bb,
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
        base_calc AS (
            SELECT
                *,
                (COALESCE(coletado, 0) - COALESCE(investido, 0)) as profit,
                COUNT(*) OVER() as total_hands,
                ROW_NUMBER() OVER(ORDER BY hand_timestamp DESC) as rn_desc
            FROM hand_metrics
        ),
        daily_metrics AS (
            SELECT
                CAST(hand_timestamp AS DATE) as session_date,
                SUM(profit) / {stake_level} as daily_profit_bb,
                CASE WHEN SUM(profit) < 0 THEN 1 ELSE 0 END as is_loss_day
            FROM base_calc
            GROUP BY CAST(hand_timestamp AS DATE)
        ),
        daily_streaks AS (
            SELECT
                session_date,
                daily_profit_bb,
                is_loss_day,
                ROW_NUMBER() OVER(ORDER BY session_date DESC) as day_rn_desc,
                ROW_NUMBER() OVER(PARTITION BY is_loss_day ORDER BY session_date DESC) as day_rn_loss_desc
            FROM daily_metrics
        ),
        global_aggs AS (
            SELECT 
                '{player_id}' as player_id,
                COUNT(*) as hands_played,
                ROUND(CAST(COALESCE((SUM(profit) / {stake_level} / NULLIF(COUNT(*), 0)) * 100, 0) AS DOUBLE), 2) as win_rate_bb100,
                ROUND(CAST(COALESCE((SUM(hero_expected_value_bb) / NULLIF(COUNT(*), 0)) * 100, 0) AS DOUBLE), 2) as ev_bb100,
                ROUND(CAST(COALESCE(SUM(hero_expected_value_bb) - (SUM(profit) / {stake_level}), 0) AS DOUBLE), 2) as ev_diff_bb,
                ROUND(CAST(COALESCE(SUM(profit) / {stake_level}, 0) AS DOUBLE), 2) as profit_bb,
                ROUND(CAST(COALESCE(AVG(vpip_flag) * 100, 0) AS DOUBLE), 2) as vpip,
                ROUND(CAST(COALESCE(AVG(pfr_flag) * 100, 0) AS DOUBLE), 2) as pfr,
                ROUND(CAST(COALESCE(SUM(agg_actions) / NULLIF(SUM(call_actions), 0), 0) AS DOUBLE), 2) as aggressiveness_factor,
                ROUND(CAST(COALESCE(AVG(all_in_flag) * 100, 0) AS DOUBLE), 2) as all_in_freq,
                ROUND(CAST(COALESCE(SUM(CASE WHEN went_to_showdown = 1 AND profit > 0 THEN 1 ELSE 0 END) / CAST(NULLIF(SUM(went_to_showdown), 0) AS DOUBLE) * 100, 0) AS DOUBLE), 2) as wsd,
                ROUND(CAST(COALESCE(SUM(CASE WHEN saw_flop_flag = 1 AND profit > 0 THEN 1 ELSE 0 END) / CAST(NULLIF(SUM(saw_flop_flag), 0) AS DOUBLE) * 100, 0) AS DOUBLE), 2) as wwsf,
                ROUND(CAST(COALESCE(AVG(CASE WHEN rn_desc <= CEIL(total_hands * 0.25) THEN vpip_flag ELSE NULL END) * 100, 0) AS DOUBLE), 2) as recent_trend_vpip,
                ROUND(CAST(COALESCE(AVG(CASE WHEN rn_desc <= CEIL(total_hands * 0.25) THEN pfr_flag ELSE NULL END) * 100, 0) AS DOUBLE), 2) as recent_trend_pfr,
                ROUND(CAST(COALESCE(SUM(CASE WHEN rn_desc <= CEIL(total_hands * 0.25) THEN profit ELSE 0 END) / {stake_level}, 0) AS DOUBLE), 2) as recent_profit_bb,
                ROUND(CAST(COALESCE(SUM(CASE WHEN rn_desc <= CEIL(total_hands * 0.25) THEN agg_actions ELSE 0 END) / NULLIF(SUM(CASE WHEN rn_desc <= CEIL(total_hands * 0.25) THEN call_actions ELSE 0 END), 0), 0) AS DOUBLE), 2) as recent_aggressiveness_factor
            FROM base_calc
        )
        SELECT 
            g.player_id,
            g.hands_played,
            g.win_rate_bb100,
            g.ev_bb100,
            g.ev_diff_bb,
            g.profit_bb,
            g.vpip,
            g.pfr,
            g.aggressiveness_factor,
            g.all_in_freq,
            g.wsd,
            g.wwsf,
            g.recent_trend_vpip,
            g.recent_trend_pfr,
            g.recent_profit_bb,
            g.recent_aggressiveness_factor,
            CAST(COALESCE((SELECT COUNT(*) FROM daily_streaks WHERE is_loss_day = 1 AND day_rn_desc = day_rn_loss_desc), 0) AS INTEGER) as current_losing_streak_sessions,
            ROUND(CAST(COALESCE((SELECT MIN(daily_profit_bb) FROM daily_streaks WHERE daily_profit_bb < 0), 0.0) AS DOUBLE), 2) as max_session_downswing_bb
        FROM global_aggs g
    """
    
    try:
        result = duckdb.query(query).fetchone()
        
        if not result or result[3] is None:
            available_games = duckdb.query(f"SELECT DISTINCT game_type FROM read_parquet('{parquet_path}')").fetchall()
            options_str = ", ".join(f"'{row[0]}'" for row in available_games if row[0])
            raise ValueError(f"Nenhum jogo encontrado para '{player_id}' no stake {stake_level} com game_type '{game_type}'.\nOpções válidas na sua base: {options_str}")

        stats = PlayerStats(
            player_id=result[0],
            time_window=TimeWindow(
                start_date=start_date,
                end_date=end_date,
                stake_level=stake_level
            ),
            global_stats=GlobalStats(
                hands_played=result[1],
                win_rate_bb100=result[2],
                ev_bb100=result[3],
                ev_diff_bb=result[4],
                profit_bb=result[5],
                vpip=result[6],
                pfr=result[7],
                aggressiveness_factor=result[8],
                all_in_freq=result[9],
                wsd=result[10],
                wwsf=result[11]
            ),
            behavioral_triggers=BehavioralTriggers(
                recent_trend_vpip=result[12],
                recent_trend_pfr=result[13],
                recent_profit_bb=result[14],
                recent_aggressiveness_factor=result[15],
                current_losing_streak_sessions=result[16],
                max_session_downswing_bb=result[17]
            )
        )
        return stats
        
    except duckdb.Error as e:
        raise RuntimeError(f"Erro interno no motor do DuckDB: {e}")

def main() -> None:
    args = parse_args()
    
    try:
        import os
        from pathlib import Path
        silver_dir = Path(os.getenv("DATALAKE_SILVER", "datalake/silver"))
        parquet_path = str(silver_dir / "hands_part_*.parquet")

        # Executa a extração matemática
        stats = extract_player_metrics(parquet_path, args.player_id, args.days, args.stake_level, args.game_type)
        
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
