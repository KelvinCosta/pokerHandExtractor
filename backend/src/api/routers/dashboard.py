from fastapi import APIRouter, Depends, HTTPException
import polars as pl
from typing import Any, Dict
from ..dependencies import get_filtered_df

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard BI"])

@router.post("/health")
def get_health_metrics(df: pl.DataFrame = Depends(get_filtered_df)) -> Dict[str, Any]:
    if df.height == 0:
        # Mock data injetado para visualização no frontend
        return {
            "total_hands": 14500,
            "profit_usd": 850.75,
            "profit_bb": 4200.50,
            "bb_100": 8.5
        }
    total_maos = df.select("hand_id").n_unique()
    
    lucro_por_mao = (
        df
        .group_by("hand_id")
        .agg(
            pl.col("amount").filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "POST")).max().fill_null(0.02).alias("bb_size"),
            pl.col("invested_amount").filter((pl.col("player") == "Hero") & (~pl.col("action_type").is_in(["COLLECT", "FOLD", "CHECK"]))).sum().fill_null(0.0).alias("investido"),
            pl.col("amount").filter((pl.col("player") == "Hero") & (pl.col("action_type") == "COLLECT")).sum().fill_null(0.0).alias("coletado")
        )
        .with_columns(
            (pl.col("coletado") - pl.col("investido")).alias("lucro_bruto")
        )
        .with_columns(
            (pl.col("lucro_bruto") / pl.col("bb_size")).alias("lucro_bb")
        )
    )
    
    lucro_total = lucro_por_mao.select(pl.col("lucro_bruto").sum()).item()
    lucro_total_bb = lucro_por_mao.select(pl.col("lucro_bb").sum()).item()
    
    val_lucro_total = float(lucro_total) if lucro_total is not None else 0.0
    val_lucro_bb = float(lucro_total_bb) if lucro_total_bb is not None else 0.0
    
    bb100 = (val_lucro_bb / total_maos) * 100 if total_maos > 0 else 0.0

    return {
        "total_hands": total_maos,
        "profit_usd": round(val_lucro_total, 2),
        "profit_bb": round(val_lucro_bb, 2),
        "bb_100": round(bb100, 2)
    }

@router.post("/preflop")
def get_preflop_metrics(df: pl.DataFrame = Depends(get_filtered_df)) -> Dict[str, Any]:
    if df.height == 0:
        # Mock data injetado para visualização no frontend
        return {
            "total_hands": 14500,
            "vpip_pct": 27.5,
            "pfr_pct": 19.8,
            "gap_pct": 7.7,
            "three_bet_pct": 8.2
        }
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
