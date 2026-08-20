from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import polars as pl
from typing import Any, Dict, List
from ..dependencies import get_filtered_df, get_filtered_hands_df, get_current_user
from ..schemas.filters import DashboardFilters
from src.database.models import User

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard BI"])

from ..dependencies import _load_user_datalake

@router.post("/metadata")
async def get_dashboard_metadata(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    cache_entry = _load_user_datalake(current_user.id)
    df = cache_entry.get("df_hands")
    
    if df is None or df.height == 0:
        return {"stakes": [], "game_types": [], "min_date": None, "max_date": None}
        
    # Obtém game_types sem filtrar por game_types
    filters_for_gt = filters.model_copy(update={'game_types': None})
    df_gt = get_filtered_df(filters_for_gt, current_user)
    
    # Obtém stakes sem filtrar por stake (mas filtrado por game_types)
    filters_for_stakes = filters.model_copy(update={'stake': None})
    df_stakes = get_filtered_df(filters_for_stakes, current_user)
        
    stakes = []
    if df_stakes.height > 0:
        if "stake_tier" in df_stakes.columns:
            stakes = df_stakes.select("stake_tier").drop_nulls().unique().sort("stake_tier").to_series().to_list()
        elif "stake_level" in df_stakes.columns:
            stakes = df_stakes.select("stake_level").drop_nulls().unique().sort("stake_level").to_series().to_list()
            
    game_types = []
    if df_gt.height > 0 and "game_type" in df_gt.columns:
        game_types = df_gt.select("game_type").drop_nulls().unique().sort("game_type").to_series().to_list()
        
    min_date = None
    max_date = None
    if "data_limpa" in df.columns:
        min_date_val = df.select(pl.col("data_limpa").drop_nulls().min()).item()
        max_date_val = df.select(pl.col("data_limpa").drop_nulls().max()).item()
        if min_date_val:
            min_date = str(min_date_val)
        if max_date_val:
            max_date = str(max_date_val)
            
    return {
        "stakes": stakes,
        "game_types": game_types,
        "min_date": min_date,
        "max_date": max_date
    }

@router.get("/hand/{hand_id}")
async def get_hand_details(hand_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    cache_entry = _load_user_datalake(current_user.id)
    df = cache_entry.get("df_hands")
    
    if df is None or df.height == 0:
        raise HTTPException(status_code=404, detail="No data available")
        
    hand_row = df.filter(pl.col("hand_id") == hand_id)
    if hand_row.height == 0:
        raise HTTPException(status_code=404, detail=f"Hand {hand_id} not found")
        
    hand_dict = hand_row.to_dicts()[0]
    
    # Garantir que a data seja serializável para JSON (converter de date para string)
    if "data_limpa" in hand_dict and hand_dict["data_limpa"]:
        hand_dict["data_limpa"] = str(hand_dict["data_limpa"])
        
    return hand_dict

@router.post("/health")
async def get_health_metrics(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    from src.api.dependencies import get_filtered_tournaments_df
    
    df = get_filtered_hands_df(filters, current_user)
    
    # Se não houver mãos, ainda podemos ter jogado apenas torneios cujo summary foi parseado?
    # Para simplificar, consideramos o dashboard atrelado primariamente às mãos.
    if df.height == 0:
        return {
            "total_hands": 0,
            "profit_usd": 0.0,
            "profit_bb": 0.0,
            "bb_100": 0.0,
            "std_dev_bb100": 0.0,
            "total_sessions": 0
        }
        
    total_maos = df.height
    
    # Agora as colunas hero_net_profit_usd e hero_net_profit_bb já vêm do ETL prontas!
    lucro_total = df.select(pl.col("hero_net_profit_usd").sum()).item()
    lucro_total_bb = df.select(pl.col("hero_net_profit_bb").sum()).item()
    
    val_lucro_total = float(lucro_total) if lucro_total is not None else 0.0
    val_lucro_bb = float(lucro_total_bb) if lucro_total_bb is not None else 0.0
    
    # Adicionar lucros reais de Torneio (Prize - Buy-in) provenientes dos sumários
    df_t = get_filtered_tournaments_df(filters, current_user)
    if df_t.height > 0:
        tourney_profit = df_t.select((pl.col("prize") - pl.col("buy_in")).sum()).item()
        val_lucro_total += float(tourney_profit) if tourney_profit is not None else 0.0
    
    bb100 = (val_lucro_bb / total_maos) * 100 if total_maos > 0 else 0.0
    
    # Standard Deviation (bb/100) = std(hero_net_profit_bb) * sqrt(100)
    std_dev_hand = df.select(pl.col("hero_net_profit_bb").std()).item()
    std_dev_bb100 = float(std_dev_hand * 10) if std_dev_hand is not None else 0.0
    
    # Sessions (Dias Jogados)
    total_sessions = df.select("data_limpa").n_unique() if "data_limpa" in df.columns else 1

    return {
        "total_hands": total_maos,
        "profit_usd": round(val_lucro_total, 2),
        "profit_bb": round(val_lucro_bb, 2),
        "bb_100": round(bb100, 2),
        "std_dev_bb100": round(std_dev_bb100, 2),
        "total_sessions": total_sessions
    }

@router.post("/health/stake-breakdown")
async def get_stake_breakdown(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    df = get_filtered_hands_df(filters, current_user)
    if df.height == 0:
        return []

    group_col = "stake_tier" if "stake_tier" in df.columns else "stake_level"
    
    if group_col not in df.columns:
        return []

    breakdown = (
        df.group_by(group_col)
        .agg(
            pl.col("hand_id").count().alias("hands"),
            pl.col("hero_net_profit_usd").sum().alias("profit_usd"),
            pl.col("hero_net_chips").sum().alias("profit_chips"),
            pl.col("hero_net_profit_bb").sum().alias("profit_bb")
        )
        .with_columns(
            (pl.col("profit_bb") / pl.col("hands") * 100).alias("winrate"),
            (pl.col("profit_usd") + pl.col("profit_chips")).alias("profit")
        )
        .sort("profit", descending=True)
    )

    result = []
    for row in breakdown.iter_rows(named=True):
        stake_val = row[group_col]
        if group_col == "stake_tier":
            stake_str = str(stake_val) if stake_val else "Unknown"
        else:
            try:
                stake_str = f"NL{int(float(stake_val) * 100)}" if stake_val is not None else "Unknown"
            except (ValueError, TypeError):
                stake_str = "Unknown"
            
        profit = row["profit"] if row["profit"] is not None else 0.0
        winrate = row["winrate"] if row["winrate"] is not None else 0.0
        
        result.append({
            "stake": stake_str,
            "hands": row["hands"] or 0,
            "profit": round(row["profit_usd"], 2), # Maintain "profit" for backwards compatibility if needed, but it's now just USD
            "profit_usd": round(row["profit_usd"], 2),
            "profit_chips": round(row["profit_chips"], 2),
            "winrate": round(winrate, 2)
        })
    return result

@router.post("/preflop")
async def get_preflop_chart(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    df = get_filtered_hands_df(filters, current_user)
    if df.height == 0:
        return {
            "total_hands": 0,
            "vpip_pct": 0.0,
            "pfr_pct": 0.0,
            "gap_pct": 0.0,
            "three_bet_pct": 0.0
        }
        
    total_maos = df.height
    
    vpip_maos = df.filter(pl.col("hero_vpip") == True).height
    pfr_maos = df.filter(pl.col("hero_pfr") == True).height
    three_bet_maos = df.filter(pl.col("hero_3bet") == True).height
    
    vpip_pct = (vpip_maos / total_maos) * 100 if total_maos > 0 else 0
    pfr_pct = (pfr_maos / total_maos) * 100 if total_maos > 0 else 0
    three_bet_pct = (three_bet_maos / total_maos) * 100 if total_maos > 0 else 0
    gap = vpip_pct - pfr_pct
    
    return {
        "total_hands": total_maos,
        "vpip_pct": round(vpip_pct, 1),
        "pfr_pct": round(pfr_pct, 1),
        "gap_pct": round(gap, 1),
        "three_bet_pct": round(three_bet_pct, 1)
    }

@router.post("/profit-trend")
async def get_profit_trend(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    from src.api.dependencies import get_filtered_tournaments_df
    
    df = get_filtered_hands_df(filters, current_user)
    df_t = get_filtered_tournaments_df(filters, current_user)
    
    if df.height == 0 and df_t.height == 0:
        return []
        
    timeline_events = []
    
    if df.height > 0:
        # Usa data_limpa (Date) para ordenação geral e date (String/Time) para tooltip
        sort_col = "data_limpa" if "data_limpa" in df.columns else "date"
        hands_events = df.select([
            pl.col(sort_col).cast(pl.Utf8).alias("sort_date"),
            pl.col("date").cast(pl.Utf8).alias("display_date"),
            pl.col("hero_net_profit_usd").cast(pl.Float64).alias("profit_event")
        ])
        timeline_events.append(hands_events)
        
    if df_t.height > 0:
        # Tentativa de extrair a data do nome do arquivo (ex: GG20260419...)
        tourneys_events = df_t.select([
            # Fallback de ordenação: tenta extrair do arquivo, se falhar joga pra '9999-99-99'
            pl.when(pl.col("source_file").str.contains(r"\d{8}"))
              .then(pl.col("source_file").str.extract(r"(\d{8})").str.replace(r"(\d{4})(\d{2})(\d{2})", r"${1}-${2}-${3} 23:59:59"))
              .otherwise(pl.lit("9999-12-31 23:59:59")).alias("sort_date"),
              
            pl.col("source_file").alias("display_date"),
            (pl.col("prize") - pl.col("buy_in")).cast(pl.Float64).alias("profit_event")
        ])
        timeline_events.append(tourneys_events)
        
    # Combina tudo em um único dataframe de eventos
    combined_df = pl.concat(timeline_events, how="vertical")
    
    # Ordena cronologicamente e calcula o cumulativo
    unique_events = (
        combined_df.sort("sort_date")
          .with_columns(
              pl.col("profit_event").cum_sum().alias("cumulative_profit")
          )
    )
    
    # Downsample para evitar gargalo de renderização no SVG (Recharts)
    max_points = 150
    if unique_events.height > max_points:
        step = unique_events.height // max_points
        unique_events = unique_events.filter(
            (pl.int_range(0, pl.len()) % step == 0) | (pl.int_range(0, pl.len()) == pl.len() - 1)
        )
    
    return unique_events.select([
        pl.col("display_date").alias("date"),
        pl.col("cumulative_profit").round(2),
        pl.col("profit_event").round(2).alias("hero_net_profit")
    ]).to_dicts()

@router.post("/monthly-profit")
async def get_monthly_profit(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    from src.api.dependencies import get_filtered_tournaments_df
    
    df = get_filtered_hands_df(filters, current_user)
    df_t = get_filtered_tournaments_df(filters, current_user)
    
    if df.height == 0 and df_t.height == 0:
        return []
        
    timeline_events = []
    
    if df.height > 0:
        sort_col = "data_limpa" if "data_limpa" in df.columns else "date"
        hands_events = df.select([
            pl.col(sort_col).cast(pl.Utf8).alias("sort_date"),
            pl.col("hero_net_profit_usd").cast(pl.Float64).alias("profit_event")
        ])
        timeline_events.append(hands_events)
        
    if df_t.height > 0:
        tourneys_events = df_t.select([
            pl.when(pl.col("source_file").str.contains(r"\d{8}"))
              .then(pl.col("source_file").str.extract(r"(\d{8})").str.replace(r"(\d{4})(\d{2})(\d{2})", r"${1}-${2}-${3}"))
              .otherwise(pl.lit("9999-12-31")).alias("sort_date"),
            (pl.col("prize") - pl.col("buy_in")).cast(pl.Float64).alias("profit_event")
        ])
        timeline_events.append(tourneys_events)
        
    combined_df = pl.concat(timeline_events, how="vertical")
    
    monthly_df = (
        combined_df.filter(pl.col("sort_date").str.starts_with("20"))
        .with_columns(
            pl.col("sort_date").str.slice(0, 7).alias("month")
        )
        .group_by("month")
        .agg(
            pl.col("profit_event").sum().alias("profit")
        )
        .sort("month")
    )
    
    return monthly_df.to_dicts()

@router.post("/analytics")
async def get_analytics_bento(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return {
            "wwsf_pct": 0.0,
            "wtsd_pct": 0.0,
            "wssd_pct": 0.0,
            "blue_line_profit": 0.0,
            "red_line_profit": 0.0
        }

    # Mãos em que o Hero viu o Flop
    hands_hero_saw_flop = (
        df.filter((pl.col("player") == pl.col("player_nickname")) & (pl.col("street") == "FLOP"))
        .select("hand_id").unique()
    )
    
    hero_won_money = (
        df.filter((pl.col("player") == pl.col("player_nickname")) & (pl.col("action_type") == "COLLECT"))
        .select("hand_id").unique()
    )
    
    # 1. WWSF (Won When Saw Flop)
    wwsf_opp = hands_hero_saw_flop.height
    wwsf_success = hands_hero_saw_flop.join(hero_won_money, on="hand_id", how="inner").height
    wwsf_pct = (wwsf_success / wwsf_opp * 100) if wwsf_opp > 0 else 0.0

    # 2. WTSD (Went to Showdown)
    showdown_hands = (
        df.select(["hand_id", "player_cards"]).unique()
        .filter(pl.col("player_cards").list.len() > 1)
        .select("hand_id")
    )
    hero_folded_any = (
        df.filter((pl.col("player") == pl.col("player_nickname")) & (pl.col("action_type") == "FOLD"))
        .select("hand_id").unique()
    )
    hero_went_to_sd = (
        showdown_hands
        .join(hands_hero_saw_flop, on="hand_id", how="inner")
        .join(hero_folded_any, on="hand_id", how="anti")
    )
    wtsd_success = hero_went_to_sd.height
    wtsd_pct = (wtsd_success / wwsf_opp * 100) if wwsf_opp > 0 else 0.0

    # 3. W$SD (Won Money at Showdown)
    wssd_success = hero_went_to_sd.join(hero_won_money, on="hand_id", how="inner").height
    wssd_pct = (wssd_success / wtsd_success * 100) if wtsd_success > 0 else 0.0

    # 4. Linhas Azul (Showdown) e Vermelha (Non-Showdown)
    df_hero_pnl = df.group_by("hand_id").agg([
        pl.col("hero_net_profit_usd").first().alias("net_usd"),
        pl.col("hero_net_chips").first().alias("net_chips")
    ])
    blue_line_profit = df_hero_pnl.join(hero_went_to_sd, on="hand_id", how="inner")["net_usd"].sum()
    red_line_profit = df_hero_pnl.join(hero_went_to_sd, on="hand_id", how="anti")["net_usd"].sum()
    blue_line_chips = df_hero_pnl.join(hero_went_to_sd, on="hand_id", how="inner")["net_chips"].sum()
    red_line_chips = df_hero_pnl.join(hero_went_to_sd, on="hand_id", how="anti")["net_chips"].sum()

    return {
        "wwsf_pct": round(wwsf_pct, 1),
        "wtsd_pct": round(wtsd_pct, 1),
        "wssd_pct": round(wssd_pct, 1),
        "blue_line_profit": round(blue_line_profit, 2),
        "red_line_profit": round(red_line_profit, 2),
        "blue_line_chips": round(blue_line_chips, 2),
        "red_line_chips": round(red_line_chips, 2)
    }

@router.post("/engines/postflop")
async def get_postflop_engines(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return {
            "cbet_flop_pct": 0.0,
            "fold_to_cbet_flop_pct": 0.0
        }

    hands_hero_saw_flop = (
        df.filter((pl.col("player") == pl.col("player_nickname")) & (pl.col("street") == "FLOP"))
        .select(["hand_id", "player_nickname"]).unique(subset=["hand_id"])
    )

    last_preflop_raise = (
        df.filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "RAISE"))
        .group_by("hand_id")
        .agg(pl.col("player").last().alias("last_aggressor"))
    )

    first_flop_bet = (
        df.filter((pl.col("street") == "FLOP") & (pl.col("action_type") == "BET"))
        .group_by("hand_id")
        .agg(pl.col("player").first().alias("first_bettor"))
    )

    hero_first_flop_action = (
        df.filter((pl.col("player") == pl.col("player_nickname")) & (pl.col("street") == "FLOP"))
        .group_by("hand_id")
        .agg(pl.col("action_type").first().alias("hero_first_action"))
    )

    flop_situations = (
        hands_hero_saw_flop
        .join(last_preflop_raise, on="hand_id", how="left")
        .join(first_flop_bet, on="hand_id", how="left")
        .join(hero_first_flop_action, on="hand_id", how="left")
    )

    # C-Bet Flop
    cbet_opp_df = flop_situations.filter(
        (pl.col("last_aggressor") == pl.col("player_nickname")) & 
        (pl.col("hero_first_action").is_in(["BET", "CHECK"]))
    )
    cbet_opp_count = cbet_opp_df.height
    cbet_success_count = cbet_opp_df.filter(pl.col("hero_first_action") == "BET").height
    cbet_flop_pct = (cbet_success_count / cbet_opp_count * 100) if cbet_opp_count > 0 else 0.0

    # Fold to C-Bet Flop
    fold_cbet_opp_df = flop_situations.filter(
        (pl.col("last_aggressor") != pl.col("player_nickname")) & 
        (pl.col("last_aggressor").is_not_null()) &
        (pl.col("first_bettor") == pl.col("last_aggressor")) &
        (pl.col("hero_first_action").is_in(["CALL", "FOLD", "RAISE"]))
    )
    fold_cbet_opp_count = fold_cbet_opp_df.height
    fold_cbet_success_count = fold_cbet_opp_df.filter(pl.col("hero_first_action") == "FOLD").height
    fold_cbet_flop_pct = (fold_cbet_success_count / fold_cbet_opp_count * 100) if fold_cbet_opp_count > 0 else 0.0

    return {
        "cbet_flop_pct": round(cbet_flop_pct, 1),
        "fold_to_cbet_flop_pct": round(fold_cbet_flop_pct, 1)
    }

from ..schemas.filters import DashboardFilters, HandsListFilters

@router.post("/hands")
async def get_hands_list(filters: HandsListFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return {"data": [], "total": 0, "page": filters.page, "limit": filters.limit}

    # Calcula as métricas base para cada mão
    df_hands_stats = (
        df.group_by("hand_id")
        .agg(
            pl.col("total_pot_final").first().alias("pot_size_usd"),
            (pl.col("hero_net_profit_usd") + pl.col("hero_net_chips")).first().alias("net_profit"),
            pl.col("stake_level").first().alias("bb_size"),
            pl.col("date").first().alias("timestamp"),
            pl.col("game_type").first().alias("game_type")
        )
        .with_columns(
            (pl.col("pot_size_usd") / pl.col("bb_size").fill_null(0.02)).alias("pot_in_bb"),
            pl.col("game_type").is_in(["Rush & Cash", "Regular Cash", "All-In or Fold"]).alias("is_cash")
        )
    )

    if df_hands_stats.height == 0:
        return {"data": [], "total": 0, "page": filters.page, "limit": filters.limit}

    # Ordenação dinâmica
    valid_sort_cols = ["timestamp", "pot_in_bb", "net_profit"]
    sort_col = filters.sort_by if filters.sort_by in valid_sort_cols else "timestamp"
    df_hands_stats = df_hands_stats.sort(sort_col, descending=filters.sort_desc)

    total_items = df_hands_stats.height
    
    # Paginação
    offset = (filters.page - 1) * filters.limit
    df_hands_stats = df_hands_stats.slice(offset, filters.limit)

    data = df_hands_stats.select([
        "hand_id", "timestamp", "game_type", "bb_size", 
        "pot_size_usd", "pot_in_bb", "net_profit", "is_cash"
    ]).to_dicts()

    # Query DB to check which hands have AI analysis or Notes
    hand_ids = [row["hand_id"] for row in data]
    from src.database.models import get_session, HandAnalysisRecord, HandNoteRecord
    db = get_session()
    try:
        analyzed_records = db.query(HandAnalysisRecord.hand_id).filter(HandAnalysisRecord.hand_id.in_(hand_ids)).all()
        analyzed_ids = {r[0] for r in analyzed_records}
        
        note_records = db.query(HandNoteRecord.hand_id).filter(
            HandNoteRecord.hand_id.in_(hand_ids),
            HandNoteRecord.user_id == current_user.id
        ).all()
        note_ids = {r[0] for r in note_records}
    except Exception:
        analyzed_ids = set()
        note_ids = set()
    finally:
        db.close()
        
    for row in data:
        row["has_analysis"] = row["hand_id"] in analyzed_ids
        row["has_note"] = row["hand_id"] in note_ids

    return {
        "data": data,
        "total": total_items,
        "page": filters.page,
        "limit": filters.limit
    }

@router.post("/engines/action-distribution")
async def get_action_distribution(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return []

    # Conta ações do Hero por Street
    hero_actions = (
        df.filter(
            (pl.col("player") == pl.col("player_nickname")) & 
            (pl.col("action_type").is_in(["FOLD", "CALL", "RAISE"]))
        )
        .group_by(["street", "action_type"])
        .agg(pl.col("hand_id").count().alias("count"))
    )

    if hero_actions.height == 0:
        return []

    # Pivot para ter FOLD, CALL, RAISE como colunas
    pivot_df = hero_actions.pivot(
        values="count",
        index="street",
        on="action_type"
    ).fill_null(0)

    # Ordem das streets
    street_order = {"PRE_FLOP": 1, "FLOP": 2, "TURN": 3, "RIVER": 4}
    street_names = {"PRE_FLOP": "Preflop", "FLOP": "Flop", "TURN": "Turn", "RIVER": "River"}

    result = []
    for row in pivot_df.iter_rows(named=True):
        f = row.get("FOLD", 0)
        c = row.get("CALL", 0)
        r = row.get("RAISE", 0)
        total = f + c + r
        if total > 0:
            result.append({
                "street_raw": row["street"],
                "street": street_names.get(row["street"], row["street"]),
                "fold": round((f / total) * 100, 1),
                "call": round((c / total) * 100, 1),
                "raise": round((r / total) * 100, 1),
                "_order": street_order.get(row["street"], 99)
            })

    # Ordena as streets logicamente
    result.sort(key=lambda x: x["_order"])
    
    # Remove colunas de suporte
    for r in result:
        del r["_order"]
        del r["street_raw"]

    return result

@router.post("/biggest-rivals")
async def get_biggest_rivals(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return []

    # Filtra as ações de todos os oponentes
    df_villains = df.filter(
        (pl.col("player") != pl.col("player_nickname")) & pl.col("player").is_not_null()
    )

    # Para somar o net profit corretamente, precisamos garantir que só contabilizamos 
    # o hero_net_profit uma vez por mão por vilão.
    df_villains_unique_hands = df_villains.unique(subset=["hand_id", "player"])

    # Agrupa por vilão para extrair estatísticas
    df_rivals = (
        df_villains.group_by("player")
        .agg(
            pl.col("hand_id").n_unique().alias("hands"),
            # VPIP: % de mãos onde o vilão deu CALL ou RAISE pre-flop
            (
                pl.col("hand_id").filter((pl.col("street") == "PRE_FLOP") & pl.col("action_type").is_in(["CALL", "RAISE"])).n_unique()
            ).alias("vpip_hands"),
            
            # PFR: % de mãos onde o vilão deu RAISE pre-flop
            (
                pl.col("hand_id").filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "RAISE")).n_unique()
            ).alias("pfr_hands"),
        )
    )
    
    # E junta com os lucros calculados a partir da base deduplicada
    df_rivals_profits = (
        df_villains_unique_hands.group_by("player")
        .agg(
            pl.col("hero_net_profit_usd").sum().alias("hero_net_usd"),
            pl.col("hero_net_chips").sum().alias("hero_net_chips"),
        )
    )
    
    df_rivals = df_rivals.join(df_rivals_profits, on="player", how="inner")

    df_rivals = (
        df_rivals.with_columns(
            (pl.col("vpip_hands") / pl.col("hands") * 100).alias("vpip"),
            (pl.col("pfr_hands") / pl.col("hands") * 100).alias("pfr"),
        )
        .sort("hands", descending=True)
        .head(100) # top 100 oponentes mais frequentes
    )

    result = []
    for i, row in enumerate(df_rivals.iter_rows(named=True)):
        vpip = row["vpip"] or 0
        pfr = row["pfr"] or 0
        
        # Define o estilo baseado no VPIP/PFR
        style = "Reg"
        if vpip > 40: style = "Fish"
        elif vpip > 30 and pfr > 20: style = "LAG"
        elif vpip < 18: style = "Nit"
        elif vpip < 25 and pfr > 15: style = "TAG"

        result.append({
            "id": f"v_{i}",
            "alias": row["player"],
            "hands": row["hands"],
            "net": round(-row["hero_net_usd"], 2), # Backward compat
            "net_usd": round(-row["hero_net_usd"], 2),
            "net_chips": round(-row["hero_net_chips"], 2),
            "vpip": round(vpip, 1),
            "pfr": round(pfr, 1),
            "style": style,
            "tags": []
        })
    return result

@router.post("/tournaments")
async def get_tournaments_list(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    from src.api.dependencies import get_filtered_tournaments_df
    
    df_t = get_filtered_tournaments_df(filters, current_user)
    
    if df_t.height == 0:
        return []
        
    df_t = df_t.with_columns([
        pl.when(pl.col("source_file").str.contains(r"\d{8}"))
          .then(pl.col("source_file").str.extract(r"(\d{8})").str.replace(r"(\d{4})(\d{2})(\d{2})", r"${1}-${2}-${3}"))
          .otherwise(pl.lit(None, dtype=pl.String)).alias("date"),
        pl.lit(0).alias("rebuys"),
        (pl.col("prize") - pl.col("buy_in")).alias("profit"),
        pl.when(pl.col("buy_in") > 0)
          .then(((pl.col("prize") - pl.col("buy_in")) / pl.col("buy_in")) * 100)
          .otherwise(0.0).alias("roi")
    ]).sort("date", descending=True, nulls_last=True).head(500)
    
    # If date is not a string, we might need to format it, but usually it's fine.
    df_t = df_t.fill_null(0)
    
    return df_t.to_dicts()


@router.get("/debug_tournaments_dup")
def debug_tournaments_dup(user_id: str = "335f7c35-320e-4671-a90e-e57062792e5a"):
    try:
        from src.api.dependencies import _load_user_datalake
        cache = _load_user_datalake(user_id)
        import polars as pl
        df_hands = cache.get("df_hands")
        
        breakdown = df_hands.group_by("game_type").agg(
            pl.count("hand_id").alias("hands"), 
            pl.col("hero_net_profit_usd").sum().alias("profit_usd")
        ).to_dicts()
        
        df = cache.get("df_tournaments", None)
        tourney_profit = 0
        tourney_height = 0
        tourney_unique = 0
        dup_profit = 0
        
        if df is not None:
            tourney_profit = df.select((pl.col("prize") - pl.col("buy_in")).sum()).item()
            tourney_height = df.height
            tourney_unique = df.unique(subset=["tournament_id", "prize", "buy_in"]).height
            
            # Duplicates profit
            dups = df.filter(df["tournament_id"].is_duplicated())
            dup_profit = dups.select((pl.col("prize") - pl.col("buy_in")).sum()).item()
            
        prefixes = df_hands.with_columns(pl.col("hand_id").str.slice(0, 2).alias("prefix")).group_by(["game_type", "prefix"]).agg(pl.count("hand_id").alias("count")).to_dicts()
            
        return {
            "total_hands": df_hands.height,
            "breakdown": breakdown,
            "tourney_profit": tourney_profit,
            "tourney_height": tourney_height,
            "tourney_unique": tourney_unique,
            "dup_profit": dup_profit,
            "prefixes": prefixes
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.post("/ranges")
def get_ranges(filters: DashboardFilters, user_id: str = "335f7c35-320e-4671-a90e-e57062792e5a"):
    """
    Returns 13x13 matrix data for the selected position and player.
    """
    try:
        from src.api.dependencies import _load_user_datalake
        import polars as pl
        import re

        cache = _load_user_datalake(user_id)
        df_hands = cache.get("df_hands")
        if df_hands is None or df_hands.height == 0:
            return {"matrix": {}}

        # Aplicar filtros (exceto posição, que pode vir separada no payload ou usar hero_position)
        if "data_limpa" in df_hands.columns:
            if filters.start_date:
                df_hands = df_hands.filter(pl.col("data_limpa") >= filters.start_date)
            if filters.end_date:
                df_hands = df_hands.filter(pl.col("data_limpa") <= filters.end_date)
                
        if filters.game_types:
            df_hands = df_hands.filter(pl.col("game_type").is_in(filters.game_types))
        
        # Opcional: filtro por posição
        position = "ALL" # Placeholder caso a gente queira permitir "ALL" ou passar num DTO
        # Se quiser ler do body, podemos adicionar 'position: str' no DashboardFilters depois
        
        # Extrai os dados das hole_cards (se a coluna existir no Parquet v4.03)
        if "hero_hole_cards" not in df_hands.columns:
            return {"error": "Por favor, clique em 'Reprocessar Datalake Automaticamente' na aba de Importação para calcular as Ranges.", "matrix": {}}

        # Pega as hole cards e filtra quem tem VPIP = True
        df_played = df_hands.filter(pl.col("hero_hole_cards").is_not_null() & (pl.col("hero_hole_cards") != ""))
        
        # Para matriz, precisamos: Total dealt (quantas vezes recebeu) e Total played (quantas vezes jogou)
        # Vamos retornar só as absolutas por enquanto, ou VPIP % (played / dealt)
        # Simplificação inicial: contagem absoluta de vezes que recebeu a mão
        def normalize_cards(cards_str):
            if not cards_str: return None
            cards = re.findall(r"([AKQJT98765432][shdc])", str(cards_str))
            if len(cards) != 2: return None
            
            ranks = "AKQJT98765432"
            r1, s1 = cards[0][0], cards[0][1]
            r2, s2 = cards[1][0], cards[1][1]
            
            try:
                if ranks.index(r1) > ranks.index(r2):
                    r1, r2 = r2, r1
                    s1, s2 = s2, s1
            except:
                return None
                
            if r1 == r2: return f"{r1}{r2}"
            elif s1 == s2: return f"{r1}{r2}s"
            else: return f"{r1}{r2}o"

        # Aplicar a normalização e contar
        # (Idealmente isso seria feito em Rust/Polars nativo, mas para MVP usamos map_elements)
        df_played = df_played.with_columns(
            pl.col("hero_hole_cards").map_elements(normalize_cards, return_dtype=pl.String).alias("range_hand")
        )
        
        df_valid = df_played.filter(pl.col("range_hand").is_not_null())
        
        # Calcula Totais Dealt
        dealt_counts = df_valid.group_by(["hero_position", "range_hand"]).len().to_dicts()
        
        # Calcula Played (VPIP == True)
        played_counts = df_valid.filter(pl.col("hero_vpip") == True).group_by(["hero_position", "range_hand"]).len().to_dicts()
        
        return {
            "dealt": dealt_counts,
            "played": played_counts
        }
        
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}

# trigger 3

class HandNoteRequest(BaseModel):
    note: str

@router.get("/hand/{hand_id}/note")
async def get_hand_note(hand_id: str, current_user: User = Depends(get_current_user)):
    from src.database.models import get_session, HandNoteRecord
    db = get_session()
    try:
        record = db.query(HandNoteRecord).filter_by(hand_id=hand_id, user_id=current_user.id).first()
        return {"note": record.note if record else ""}
    finally:
        db.close()

@router.post("/hand/{hand_id}/note")
async def save_hand_note(hand_id: str, req: HandNoteRequest, current_user: User = Depends(get_current_user)):
    from src.database.models import get_session, HandNoteRecord
    import uuid
    db = get_session()
    try:
        record = db.query(HandNoteRecord).filter_by(hand_id=hand_id, user_id=current_user.id).first()
        if record:
            record.note = req.note
        else:
            record = HandNoteRecord(
                id=str(uuid.uuid4()),
                hand_id=hand_id,
                user_id=current_user.id,
                note=req.note
            )
            db.add(record)
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

class VillainNoteRequest(BaseModel):
    note: str

@router.get("/villains/{player}/tag")
async def get_villain_tag(player: str, current_user: User = Depends(get_current_user)):
    from src.database.models import get_session, VillainNoteRecord
    db = get_session()
    try:
        record = db.query(VillainNoteRecord).filter_by(player=player, user_id=current_user.id).first()
        return {"note": record.note if record else ""}
    finally:
        db.close()

@router.post("/villains/{player}/tag")
async def save_villain_tag(player: str, req: VillainNoteRequest, current_user: User = Depends(get_current_user)):
    from src.database.models import get_session, VillainNoteRecord
    import uuid
    db = get_session()
    try:
        record = db.query(VillainNoteRecord).filter_by(player=player, user_id=current_user.id).first()
        if record:
            record.note = req.note
        else:
            record = VillainNoteRecord(
                id=str(uuid.uuid4()),
                player=player,
                user_id=current_user.id,
                note=req.note
            )
            db.add(record)
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

@router.post("/engines/cbet-textures")
async def get_cbet_textures(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    from src.api.dependencies import get_filtered_df, get_filtered_hands_df
    df = get_filtered_df(filters, current_user)
    df_hands = get_filtered_hands_df(filters, current_user)
    
    if df.height == 0:
        return {"scatter": [], "valueOwning": []}
        
    df_pfr_hero = (
        df.filter(
            (pl.col("player") == pl.col("player_nickname")) & 
            (pl.col("street") == "PRE_FLOP") & 
            (pl.col("action_type") == "RAISE")
        )
        .select("hand_id").unique()
    )

    df_flop_action_hero = (
        df.filter(
            (pl.col("player") == pl.col("player_nickname")) & 
            (pl.col("street") == "FLOP")
        )
        .select("hand_id").unique()
    )

    df_cbet_oportunidades = df_pfr_hero.join(df_flop_action_hero, on="hand_id", how="inner")
    
    df_cbet_executada = (
        df.filter(
            (pl.col("player") == pl.col("player_nickname")) & 
            (pl.col("street") == "FLOP") & 
            (pl.col("action_type") == "BET")
        )
        .join(df_cbet_oportunidades, on="hand_id", how="inner") 
    )

    df_pot_flop = (
        df.filter(pl.col("street") == "PRE_FLOP")
        .group_by("hand_id")
        .agg(pl.col("amount").sum().alias("pote_real_flop"))
    )
    
    df_hero_flop_bet = (
        df.filter((pl.col("player") == pl.col("player_nickname")) & (pl.col("street") == "FLOP") & (pl.col("action_type") == "BET"))
        .select(["hand_id", "amount"])
    )

    if "flop_suit_type" in df_hands.columns and "flop_pair_type" in df_hands.columns:
        df_texturas = (
            df_hands.select(["hand_id", "flop_suit_type", "flop_pair_type"])
            .drop_nulls(subset=["flop_suit_type", "flop_pair_type"])
        )
    else:
        df_texturas = pl.DataFrame({"hand_id": [], "flop_suit_type": [], "flop_pair_type": []}, schema={"hand_id": pl.Utf8, "flop_suit_type": pl.Utf8, "flop_pair_type": pl.Utf8})

    df_stake = df_hands.select(["hand_id", "stake_level"])

    df_cbet_range = (
        df_cbet_executada.select("hand_id")
        .unique()
        .join(df_hero_flop_bet, on="hand_id", how="left")
        .join(df_pot_flop, on="hand_id", how="left")
        .join(df_texturas, on="hand_id", how="left")
        .join(df_stake, on="hand_id", how="left")
        .with_columns(
            ((pl.col("amount") / pl.col("pote_real_flop")) * 100).round(1).alias("sizing_flop_pct"),
            pl.when(pl.col("stake_level") > 0)
            .then((pl.col("amount") / pl.col("stake_level")))
            .otherwise(0.0)
            .round(1)
            .alias("hero_bet_bb")
        )
    )

    scatter_df = df_cbet_range.drop_nulls(subset=["flop_suit_type", "sizing_flop_pct"]).select(["hand_id", "flop_suit_type", "sizing_flop_pct"]).to_dicts()

    # Value Owning Tracker
    flop_calls_raises = (
        df.filter((pl.col("street") == "FLOP") & (pl.col("player") != pl.col("player_nickname")) & (pl.col("action_type").is_in(["CALL", "RAISE"])))
        .select("hand_id").unique()
    )
    
    showdown_hands = (
        df_hands.select(["hand_id", "player_cards"])
        .filter(pl.col("player_cards").list.len() > 1)
        .select("hand_id")
    )

    from src.dashboard.domain_data import get_vencedores_df
    try:
        vencedores_df = get_vencedores_df(df_hands)
        df_value_owning = (
            df_cbet_range
            .filter(pl.col("sizing_flop_pct") > 60.0)
            .join(flop_calls_raises, on="hand_id", how="inner")
            .join(showdown_hands, on="hand_id", how="inner")
            .join(vencedores_df, on="hand_id", how="inner")
            .filter(pl.col("hero_ganhou") == False)
            .select(["hand_id", "flop_suit_type", "sizing_flop_pct", pl.col("pote_real_flop").alias("pote_no_flop"), pl.col("amount").alias("hero_bet"), "hero_bet_bb"])
            .sort("sizing_flop_pct", descending=True)
        )
        vo_list = df_value_owning.to_dicts()
    except Exception:
        vo_list = []

    return {
        "scatter": scatter_df,
        "valueOwning": vo_list
    }

@router.post("/engines/river-audit")
async def get_river_audit(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    from src.api.dependencies import get_filtered_df, get_filtered_hands_df
    df = get_filtered_df(filters, current_user)
    df_hands = get_filtered_hands_df(filters, current_user)
    
    if df.height == 0:
        return {"hero_bets": [], "hero_calls": [], "summary": {}}

    auditoria_base = (
        df
        .filter(
            (pl.col("hand_id").str.starts_with("RC")) & 
            (pl.col("street") == "RIVER")
        )
        .group_by("hand_id")
        .agg(
            pl.col("current_pot").first().alias("pote_final"),
            pl.col("invested_amount").filter(pl.col("action_type").is_in(["BET", "CALL", "RAISE"])).sum().alias("investimento_total_river"),
            pl.col("invested_amount").filter((pl.col("player") == pl.col("player_nickname")) & (pl.col("action_type") == "BET")).sum().alias("hero_bet_amount"),
            pl.col("is_all_in").filter((pl.col("player") == pl.col("player_nickname")) & (pl.col("action_type") == "BET")).any().alias("hero_all_in_river"),
            pl.col("player").filter((pl.col("player") != pl.col("player_nickname")) & (pl.col("action_type") == "CALL")).count().alias("qtd_calls_recebidos")
        )
        .filter((pl.col("hero_bet_amount") > 0) & (pl.col("qtd_calls_recebidos") > 0))
        .with_columns(
            pl.when(pl.col("pote_final") - pl.col("investimento_total_river") <= 0)
            .then(0.01)
            .otherwise(pl.col("pote_final") - pl.col("investimento_total_river"))
            .alias("pote_anterior")
        )
        .with_columns(((pl.col("hero_bet_amount") / pl.col("pote_anterior")) * 100).round(1).alias("sizing_pct"))
    )

    from src.dashboard.domain_data import get_vencedores_df
    try:
        vencedores_df = get_vencedores_df(df_hands)
        auditoria_ev = (
            auditoria_base
            .join(vencedores_df, on="hand_id", how="left")
            .with_columns(
                pl.when(pl.col("hero_ganhou") == True).then(pl.lit("WON")).otherwise(pl.lit("LOST")).alias("resultado")
            )
            .with_columns(
                (pl.col("pote_anterior") * 0.75).round(2).alias("bet_ideal_75")
            )
            .with_columns(
                (pl.col("bet_ideal_75") - pl.col("hero_bet_amount")).round(2).alias("diferenca_dolares")
            )
            .with_columns(
                pl.when(pl.col("hero_all_in_river")).then(pl.lit("All-In"))
                .when((pl.col("resultado") == "WON") & (pl.col("diferenca_dolares") > 0)).then(pl.lit("Missed Value"))
                .when((pl.col("resultado") == "LOST") & (pl.col("diferenca_dolares") > 0)).then(pl.lit("Saved"))
                .when((pl.col("resultado") == "WON") & (pl.col("diferenca_dolares") < 0)).then(pl.lit("Max Extraction"))
                .when((pl.col("resultado") == "LOST") & (pl.col("diferenca_dolares") < 0)).then(pl.lit("Wasted"))
                .otherwise(pl.lit("Optimal")).alias("impacto_no_caixa")
            )
            .sort("sizing_pct", descending=False)
        )
        
        
        # Fill NaN to avoid returning math.nan
        auditoria_ev = auditoria_ev.with_columns(
            pl.col("diferenca_dolares").fill_nan(0.0).fill_null(0.0)
        )
        
        lucro_perdido = auditoria_ev.filter((pl.col("resultado") == "WON") & (pl.col("diferenca_dolares") > 0))["diferenca_dolares"].sum()
        dinheiro_salvo = auditoria_ev.filter((pl.col("resultado") == "LOST") & (pl.col("diferenca_dolares") > 0))["diferenca_dolares"].sum()
        
        lucro_perdido = float(lucro_perdido) if lucro_perdido is not None else 0.0
        dinheiro_salvo = float(dinheiro_salvo) if dinheiro_salvo is not None else 0.0
        
        import math
        if math.isnan(lucro_perdido): lucro_perdido = 0.0
        if math.isnan(dinheiro_salvo): dinheiro_salvo = 0.0
        
        balanco_real = lucro_perdido - dinheiro_salvo
        
        hero_bets = auditoria_ev.to_dicts()
    except Exception as e:
        import logging
        logging.error(f"Error in river-audit: {e}")
        hero_bets = []
        lucro_perdido = 0.0
        dinheiro_salvo = 0.0
        balanco_real = 0.0

    df_hero_calls_river = (
        df.filter(
            (pl.col("player") == pl.col("player_nickname")) & 
            (pl.col("street") == "RIVER") & 
            (pl.col("action_type") == "CALL")
        )
        .select(["hand_id", "amount"])
        .rename({"amount": "valor_do_call"})
    )

    try:
        auditoria_calls = (
            df_hero_calls_river
            .join(vencedores_df, on="hand_id", how="left")
            .with_columns(
                pl.when(pl.col("hero_ganhou") == True).then(pl.lit("Hero Call")).otherwise(pl.lit("Crying Call")).alias("resultado")
            )
            .sort("valor_do_call", descending=True)
        )
        hero_calls = auditoria_calls.to_dicts()
    except Exception:
        hero_calls = []

    return {
        "hero_bets": hero_bets,
        "hero_calls": hero_calls,
        "summary": {
            "missed_value": lucro_perdido,
            "saved_money": dinheiro_salvo,
            "net_leak": balanco_real
        }
    }
