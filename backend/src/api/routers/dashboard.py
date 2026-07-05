from fastapi import APIRouter, Depends, HTTPException
import polars as pl
from typing import Any, Dict, List
from ..dependencies import get_filtered_df, get_filtered_hands_df, get_current_user
from ..schemas.filters import DashboardFilters
from src.database.models import User

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard BI"])

@router.post("/health")
def get_health_metrics(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    df = get_filtered_hands_df(filters, current_user)
    if df.height == 0:
        return {
            "total_hands": 0,
            "profit_usd": 0.0,
            "profit_bb": 0.0,
            "bb_100": 0.0
        }
        
    hero = filters.hero_name
    total_maos = df.height
    
    lucro_por_mao = df.with_columns(
        (pl.col("hero_net_profit") / pl.col("stake_level")).alias("lucro_bb")
    )
    
    lucro_total = lucro_por_mao.select(pl.col("hero_net_profit").sum()).item()
    lucro_total_bb = lucro_por_mao.select(pl.col("lucro_bb").sum()).item()
    
    val_lucro_total = float(lucro_total) if lucro_total is not None else 0.0
    val_lucro_bb = float(lucro_total_bb) if lucro_total_bb is not None else 0.0
    
    bb100 = (val_lucro_bb / total_maos) * 100 if total_maos > 0 else 0.0
    
    # Standard Deviation (bb/100) = std(lucro_bb_por_mao) * sqrt(100)
    std_dev_hand = lucro_por_mao.select(pl.col("lucro_bb").std()).item()
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

@router.post("/preflop")
def get_preflop_chart(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
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
def get_profit_trend(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    df = get_filtered_hands_df(filters, current_user)
    if df.height == 0:
        return []
        
    unique_hands = (
        df.sort("data_limpa" if "data_limpa" in df.columns else "date")
          .with_columns(
              pl.col("hero_net_profit").cum_sum().alias("cumulative_profit")
          )
    )
    
    # Downsample para evitar gargalo de renderização no SVG (Recharts)
    max_points = 150
    if unique_hands.height > max_points:
        step = unique_hands.height // max_points
        # Pegar 1 a cada N pontos, ou se for a última linha (para o lucro final bater exato)
        unique_hands = unique_hands.filter(
            (pl.int_range(0, pl.len()) % step == 0) | (pl.int_range(0, pl.len()) == pl.len() - 1)
        )
    
    return unique_hands.select([
        "date",
        "cumulative_profit",
        "hero_net_profit"
    ]).to_dicts()

@router.post("/analytics")
def get_analytics_bento(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
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
        df.filter((pl.col("player") == filters.hero_name) & (pl.col("street") == "FLOP"))
        .select("hand_id").unique()
    )
    
    hero_won_money = (
        df.filter((pl.col("player") == filters.hero_name) & (pl.col("action_type") == "COLLECT"))
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
        df.filter((pl.col("player") == filters.hero_name) & (pl.col("action_type") == "FOLD"))
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
    df_hero_pnl = df.group_by("hand_id").agg(pl.col("hero_net_profit").first().alias("net_profit"))
    blue_line_profit = df_hero_pnl.join(hero_went_to_sd, on="hand_id", how="inner")["net_profit"].sum()
    red_line_profit = df_hero_pnl.join(hero_went_to_sd, on="hand_id", how="anti")["net_profit"].sum()

    return {
        "wwsf_pct": round(wwsf_pct, 1),
        "wtsd_pct": round(wtsd_pct, 1),
        "wssd_pct": round(wssd_pct, 1),
        "blue_line_profit": round(blue_line_profit, 2),
        "red_line_profit": round(red_line_profit, 2)
    }

@router.post("/engines/postflop")
def get_postflop_engines(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return {
            "cbet_flop_pct": 0.0,
            "fold_to_cbet_flop_pct": 0.0
        }

    hands_hero_saw_flop = (
        df.filter((pl.col("player") == filters.hero_name) & (pl.col("street") == "FLOP"))
        .select("hand_id").unique()
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
        df.filter((pl.col("player") == filters.hero_name) & (pl.col("street") == "FLOP"))
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
        (pl.col("last_aggressor") == filters.hero_name) & 
        (pl.col("hero_first_action").is_in(["BET", "CHECK"]))
    )
    cbet_opp_count = cbet_opp_df.height
    cbet_success_count = cbet_opp_df.filter(pl.col("hero_first_action") == "BET").height
    cbet_flop_pct = (cbet_success_count / cbet_opp_count * 100) if cbet_opp_count > 0 else 0.0

    # Fold to C-Bet Flop
    fold_cbet_opp_df = flop_situations.filter(
        (pl.col("last_aggressor") != filters.hero_name) & 
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

@router.post("/big-pots")
def get_big_pots(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> list[Dict[str, Any]]:
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return []

    # 1. Identificar Potes Grandes
    df_pot_sizes = (
        df.group_by("hand_id")
        .agg(
            pl.col("total_pot_final").first().alias("pot_size_usd"),
            pl.col("hero_net_profit").first().alias("net_profit"),
            pl.col("amount").filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "POST")).max().fill_null(0.02).alias("bb_size"),
            pl.col("date").first().alias("timestamp")
        )
        .with_columns(
            (pl.col("pot_size_usd") / pl.col("bb_size")).alias("pot_in_bb")
        )
        .filter(pl.col("pot_in_bb") >= 40.0)
        .sort("pot_in_bb", descending=True)
        .head(50) # Top 50 biggest pots to avoid payload bloat
    )

    if df_pot_sizes.height == 0:
        return []

    return df_pot_sizes.select([
        "hand_id",
        "timestamp",
        "pot_in_bb",
        "net_profit"
    ]).to_dicts()
