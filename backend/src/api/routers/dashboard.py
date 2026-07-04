from fastapi import APIRouter, Depends, HTTPException
import polars as pl
from typing import Any, Dict
from ..dependencies import get_filtered_df

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard BI"])

@router.post("/health")
def get_health_metrics(df: pl.DataFrame = Depends(get_filtered_df)) -> Dict[str, Any]:
    # Mock data injetado para visualização no frontend
    return {
        "total_hands": 37920,
        "profit_usd": 184920.00,
        "profit_bb": 4200.50,
        "bb_100": 6.8
    }

    # ----- Lógica Real Temporariamente Desativada -----
    total_maos = df.select("hand_id").n_unique()

@router.post("/preflop")
def get_preflop_metrics(df: pl.DataFrame = Depends(get_filtered_df)) -> Dict[str, Any]:
    # Mock data injetado para visualização no frontend
    return {
        "total_hands": 37920,
        "vpip_pct": 27.5,
        "pfr_pct": 19.8,
        "gap_pct": 7.7,
        "three_bet_pct": 8.2
    }

    # ----- Lógica Real Temporariamente Desativada -----
    total_maos = df.select("hand_id").n_unique()
    df_pf = df.filter(pl.col("street") == "PRE_FLOP")
    
    # 3-Bet logic
    df_pf = df_pf.with_columns(
        pl.col("action_type").eq("RAISE").cum_sum().over("hand_id").alias("raises_so_far")
    )
    
    vpip_maos = df_pf.filter((pl.col("player") == "Hero") & (pl.col("action_type").is_in(["CALL", "BET", "RAISE"]))).select("hand_id").n_unique()
    pfr_maos = df_pf.filter((pl.col("player") == "Hero") & (pl.col("action_type").is_in(["BET", "RAISE"]))).select("hand_id").n_unique()
    three_bet_maos = df_pf.filter((pl.col("player") == "Hero") & (pl.col("action_type") == "RAISE") & (pl.col("raises_so_far") >= 2)).select("hand_id").n_unique()
    
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
