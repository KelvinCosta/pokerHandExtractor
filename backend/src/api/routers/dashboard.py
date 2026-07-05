from fastapi import APIRouter, Depends, HTTPException
import polars as pl
from typing import Any, Dict
from ..dependencies import get_filtered_df, get_current_user
from ..schemas.filters import DashboardFilters
from src.database.models import User

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard BI"])

@router.post("/health")
def get_health_metrics(filters: DashboardFilters, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return {
            "total_hands": 0,
            "profit_usd": 0.0,
            "profit_bb": 0.0,
            "bb_100": 0.0
        }
        
    hero = filters.hero_name
    total_maos = df.select("hand_id").n_unique()
    
    lucro_por_mao = (
        df
        .group_by("hand_id")
        .agg(
            pl.col("amount").filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "POST")).max().fill_null(0.02).alias("bb_size"),
            pl.col("hero_net_profit").first(),
            pl.col("hero_position").first(),
            pl.col("hero_vpip").first(),
            pl.col("hero_pfr").first(),
            pl.col("hero_3bet").first()
        )
        .with_columns(
            (pl.col("hero_net_profit") / pl.col("bb_size")).alias("lucro_bb")
        )
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
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return {
            "total_hands": 0,
            "vpip_pct": 0.0,
            "pfr_pct": 0.0,
            "gap_pct": 0.0,
            "three_bet_pct": 0.0
        }
        
    total_maos = df.select("hand_id").n_unique()
    
    # Pega apenas uma linha por mão
    unique_hands = df.unique(subset=["hand_id"], keep="first")
    
    vpip_maos = unique_hands.filter(pl.col("hero_vpip") == True).height
    pfr_maos = unique_hands.filter(pl.col("hero_pfr") == True).height
    three_bet_maos = unique_hands.filter(pl.col("hero_3bet") == True).height
    
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
def get_profit_trend(filters: DashboardFilters, current_user: User = Depends(get_current_user)):
    df = get_filtered_df(filters, current_user)
    if df.height == 0:
        return []
        
    unique_hands = (
        df.unique(subset=["hand_id"], keep="first")
          .sort("date")
          .with_columns(
              pl.col("hero_net_profit").cum_sum().alias("cumulative_profit")
          )
    )
    
    return unique_hands.select([
        "date",
        "cumulative_profit",
        "hero_net_profit"
    ]).to_dicts()
