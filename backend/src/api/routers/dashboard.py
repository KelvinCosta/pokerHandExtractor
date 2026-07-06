from fastapi import APIRouter, Depends, HTTPException
import polars as pl
from typing import Any, Dict, List
from ..dependencies import get_filtered_df, get_filtered_hands_df, get_current_user
from ..schemas.filters import DashboardFilters
from src.database.models import User

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard BI"])

from ..dependencies import _load_user_datalake

@router.get("/metadata")
async def get_dashboard_metadata(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    cache_entry = _load_user_datalake(current_user.id, "silver-layer")
    df = cache_entry.get("df_hands")
    
    if df is None or df.height == 0:
        return {"stakes": [], "game_types": [], "min_date": None, "max_date": None}
        
    stakes = []
    if "stake_level" in df.columns:
        stakes = df.select("stake_level").drop_nulls().unique().sort("stake_level").to_series().to_list()
        
    game_types = []
    if "game_type" in df.columns:
        game_types = df.select("game_type").drop_nulls().unique().sort("game_type").to_series().to_list()
        
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
    import os
    silver_bucket = os.getenv("S3_SILVER_BUCKET", "poker-silver")
    cache_entry = _load_user_datalake(current_user.id, silver_bucket)
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

    if "stake_level" not in df.columns:
        return []

    breakdown = (
        df.group_by("stake_level")
        .agg(
            pl.col("hand_id").count().alias("hands"),
            pl.col("hero_net_profit_usd").sum().alias("profit"),
            pl.col("hero_net_profit_bb").sum().alias("profit_bb")
        )
        .with_columns(
            (pl.col("profit_bb") / pl.col("hands") * 100).alias("winrate")
        )
        .sort("profit", descending=True)
    )

    result = []
    for row in breakdown.iter_rows(named=True):
        stake_val = row["stake_level"]
        try:
            stake_str = f"NL{int(float(stake_val) * 100)}" if stake_val is not None else "Unknown"
        except (ValueError, TypeError):
            stake_str = "Unknown"
            
        profit = row["profit"] if row["profit"] is not None else 0.0
        winrate = row["winrate"] if row["winrate"] is not None else 0.0
        
        result.append({
            "stake": stake_str,
            "hands": row["hands"] or 0,
            "profit": round(profit, 2),
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
            pl.col("hero_net_profit_usd").alias("profit_event")
        ])
        timeline_events.append(hands_events)
        
    if df_t.height > 0:
        # Tentativa de extrair a data do nome do arquivo (ex: GG20260419...)
        tourneys_events = df_t.select([
            # Fallback de ordenação: tenta extrair do arquivo, se falhar joga pra '9999-99-99'
            pl.when(pl.col("source_file").str.contains(r"\d{8}"))
              .then(pl.col("source_file").str.extract(r"(\d{8})").str.replace(r"(\d{4})(\d{2})(\d{2})", r"${1}-${2}-${3}"))
              .otherwise(pl.lit("9999-12-31")).alias("sort_date"),
              
            pl.col("source_file").alias("display_date"),
            (pl.col("prize") - pl.col("buy_in")).alias("profit_event")
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
    df_hero_pnl = df.group_by("hand_id").agg((pl.col("hero_net_profit_usd") + pl.col("hero_net_chips")).first().alias("net_profit"))
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

    return {
        "data": df_hands_stats.select([
            "hand_id",
            "timestamp",
            "pot_in_bb",
            "net_profit",
            "is_cash"
        ]).to_dicts(),
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

    # Agrupa por vilão para extrair estatísticas
    df_rivals = (
        df_villains.group_by("player")
        .agg(
            pl.col("hand_id").n_unique().alias("hands"),
            # Para net profit do vilão, se o hero perdeu X na mão, o vilão não necessariamente ganhou X 
            # (pode ter sido um pote multiway). Mas para simplificar a rivalidade, consideramos o 
            # (net profit do hero invertido) caso a mão tenha ido pra showdown entre os dois, ou apenas 
            # o sum(hero_net_profit) de quando eles estavam na mesma mesa.
            # O jeito certo é agregar o net profit do Hero por mão, e inverter
            (pl.col("hero_net_profit_usd") + pl.col("hero_net_chips")).first().sum().alias("hero_net_total"),
            
            # VPIP: % de mãos onde o vilão deu CALL ou RAISE pre-flop
            (
                pl.col("hand_id").filter((pl.col("street") == "PRE_FLOP") & pl.col("action_type").is_in(["CALL", "RAISE"])).n_unique()
            ).alias("vpip_hands"),
            
            # PFR: % de mãos onde o vilão deu RAISE pre-flop
            (
                pl.col("hand_id").filter((pl.col("street") == "PRE_FLOP") & (pl.col("action_type") == "RAISE")).n_unique()
            ).alias("pfr_hands"),
        )
        .with_columns(
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
            "net": round(-row["hero_net_total"], 2), # Inverte para "net do vilão" (negativo = ele nos tirou dinheiro)
            "vpip": round(vpip, 1),
            "pfr": round(pfr, 1),
            "threeBet": round(pfr * 0.35, 1), # mock heurístico derivado do PFR por enquanto
            "wtsd": 25.0, # mock
            "style": style,
            "tags": []
        })
    return result
