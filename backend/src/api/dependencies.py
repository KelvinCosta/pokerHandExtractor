import os
from pathlib import Path
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import polars as pl
from .schemas.filters import DashboardFilters
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.database.models import User
from src.core.security import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user() -> User:
    # MVP Offline: Bypass authentication and return a mock user
    # This ID must be a fixed UUID so that the datalake folder is consistent
    return User(id="335f7c35-320e-4671-a90e-e57062792e5a", email="mvp@offline.local")


import time
import threading

_DATALAKE_CACHE = {}  # { user_id: {"df": pl.DataFrame, "timestamp": float} }
_CACHE_LOCK = threading.Lock()

def invalidate_cache(user_id: str):
    """Limpa o cache do Datalake em memória para o usuário (chamado após o ETL)"""
    with _CACHE_LOCK:
        if user_id in _DATALAKE_CACHE:
            del _DATALAKE_CACHE[user_id]

def _apply_filters(df: pl.DataFrame, filters: DashboardFilters) -> pl.DataFrame:
    # Filtro de Data (já usando a coluna pré-processada pelo cache)
    if "data_limpa" in df.columns:
        if filters.start_date:
            df = df.filter(pl.col("data_limpa") >= filters.start_date)
        if filters.end_date:
            df = df.filter(pl.col("data_limpa") <= filters.end_date)
            
    # Filtro de Busca Textual (ID da mão ou Oponentes ou Arquivo)
    if filters.search_query:
        sq = filters.search_query.lower()
        if "player" in df.columns:
            cond = pl.col("hand_id").str.to_lowercase().str.contains(sq, literal=True) | pl.col("player").str.to_lowercase().str.contains(sq, literal=True)
            if "source_file" in df.columns:
                cond = cond | pl.col("source_file").str.to_lowercase().str.contains(sq, literal=True)
            if "game_info" in df.columns:
                cond = cond | pl.col("game_info").str.to_lowercase().str.contains(sq, literal=True)

            
            # Encontra os hand_ids que tem match com a busca
            matching_hands = df.filter(cond).select("hand_id").unique()
            
            # Mantém todas as ações dessas mãos intactas
            df = df.join(matching_hands, on="hand_id", how="inner")
        else:
            cond = pl.col("hand_id").str.to_lowercase().str.contains(sq, literal=True)
            if "source_file" in df.columns:
                cond = cond | pl.col("source_file").str.to_lowercase().str.contains(sq, literal=True)
            if "game_info" in df.columns:
                cond = cond | pl.col("game_info").str.to_lowercase().str.contains(sq, literal=True)
            df = df.filter(cond)

    if filters.hole_cards_range and "hero_hole_cards" in df.columns:
        import re
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
            
        df = df.filter(pl.col("hero_hole_cards").map_elements(normalize_cards, return_dtype=pl.String) == filters.hole_cards_range)

    if filters.hero_position and "hero_position" in df.columns:
        df = df.filter(pl.col("hero_position") == filters.hero_position)

    # Filtro Dinâmico de Tipo de Jogo
    if filters.game_types:
        if "game_type" in df.columns:
            df = df.filter(pl.col("game_type").is_in(filters.game_types))
        else:
            # Fallback provisório baseado no prefixo do hand_id
            exprs = []
            if "Rush & Cash" in filters.game_types:
                exprs.append(pl.col("hand_id").str.starts_with("RC"))
            if "Tournament" in filters.game_types:
                exprs.append(pl.col("hand_id").str.starts_with("SG") | pl.col("hand_id").str.starts_with("TM"))
            if "Regular Cash" in filters.game_types or "Regular" in filters.game_types:
                exprs.append(pl.col("hand_id").str.starts_with("HD"))
            if "All-In or Fold" in filters.game_types:
                exprs.append(pl.col("hand_id").str.starts_with("AF"))
            
            if exprs:
                # Faz um OR entre todas as expressões válidas
                combined_expr = exprs[0]
                for e in exprs[1:]:
                    combined_expr = combined_expr | e
                df = df.filter(combined_expr)
            else:
                # Se mandou um tipo não suportado pelo fallback, zera o df
                df = df.filter(pl.lit(False))
            
    # Filtro de Nível de Aposta (Stake)
    if filters.stake is not None:
        if "stake_tier" in df.columns:
            df = df.filter(pl.col("stake_tier") == filters.stake)
        elif "stake_level" in df.columns:
            # Fallback para float caso a base ainda não tenha sido atualizada
            try:
                stake_float = float(filters.stake)
                df = df.filter((pl.col("stake_level") - stake_float).abs() < 0.001)
            except ValueError:
                pass
        
    # Filtro de Plataforma (Novo)
    if filters.platforms and "platform" in df.columns:
        df = df.filter(pl.col("platform").is_in(filters.platforms))

    return df

def _load_user_datalake(user_id: str) -> dict:
    # Fast path sem lock
    if user_id in _DATALAKE_CACHE:
        return _DATALAKE_CACHE[user_id]
        
    with _CACHE_LOCK:
        # Double-check locking pattern
        if user_id in _DATALAKE_CACHE:
            return _DATALAKE_CACHE[user_id]

        try:
            safe_user_id = os.path.basename(str(user_id))
            silver_dir = Path(os.getenv("DATALAKE_SILVER", "data/silver")) / safe_user_id
            parquet_files = list(silver_dir.glob("hands_part_*.parquet"))
            
            if not parquet_files:
                empty_df = pl.DataFrame(schema={"hand_id": pl.Utf8, "platform": pl.Utf8})
                cache_entry = {"df_hands": empty_df, "df_actions": empty_df, "timestamp": time.time()}
                _DATALAKE_CACHE[user_id] = cache_entry
                return cache_entry

            local_path = str(silver_dir / "hands_part_*.parquet")
            df_hands = pl.scan_parquet(local_path).collect()
            df_hands = df_hands.unique(subset=["hand_id"], keep="last", maintain_order=True)

            nome_coluna_data = "date" if "date" in df_hands.columns else "timestamp" if "timestamp" in df_hands.columns else None
            if nome_coluna_data:
                df_hands = df_hands.with_columns(
                    pl.col(nome_coluna_data).str.to_datetime("%Y/%m/%d %H:%M:%S", strict=False).dt.date().alias("data_limpa")
                )

            df_actions = df_hands.explode("actions").unnest("actions")
            
            # Carregar sumários de torneios se existirem
            df_tournaments = pl.DataFrame()
            try:
                local_tournaments_path = silver_dir / "tournaments.parquet"
                if local_tournaments_path.exists():
                    df_tournaments = pl.scan_parquet(str(local_tournaments_path)).collect()
                    if "tournament_id" in df_tournaments.columns:
                        df_tournaments = df_tournaments.unique(subset=["tournament_id"], keep="last", maintain_order=True)
            except Exception:
                pass # Se não houver arquivo de torneios, segue normalmente com df vazio
            
            cache_entry = {"df_hands": df_hands, "df_actions": df_actions, "df_tournaments": df_tournaments, "timestamp": time.time()}
            _DATALAKE_CACHE[user_id] = cache_entry
            return cache_entry
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler o datalake local: {e}")

def get_filtered_df(filters: DashboardFilters, user: User) -> pl.DataFrame:
    """Retorna o Datalake EXPLODIDO no nível da Ação (usado por Analytics/Postflop/BigPots)"""
    cache_entry = _load_user_datalake(user.id)
    return _apply_filters(cache_entry["df_actions"], filters)

def get_filtered_hands_df(filters: DashboardFilters, user: User) -> pl.DataFrame:
    """Retorna o Datalake base SEM explodir (Otimizado! Usado por Health/Preflop/Trend)"""
    cache_entry = _load_user_datalake(user.id)
    return _apply_filters(cache_entry["df_hands"], filters)

def get_filtered_tournaments_df(filters: DashboardFilters, user: User) -> pl.DataFrame:
    """Retorna os Sumários de Torneios filtrados (usado para compor o Profit total)"""
    cache_entry = _load_user_datalake(user.id)
    df_t = cache_entry.get("df_tournaments", pl.DataFrame())
    
    if df_t.height == 0:
        return df_t
        
    if filters.game_types:
        # Verifica se algum dos tipos selecionados é de torneio
        tournament_types = ["Tournament", "Spin & Gold", "Mystery Battle Royale"]
        has_tournament_type = any(t in filters.game_types for t in tournament_types)
        
        if not has_tournament_type:
            # Se filtrou apenas por Cash Games, não retorna nada dos sumários
            return df_t.clear()
            
        # Opcional: Se a gente quisesse ser muito restrito, a gente poderia olhar o source_file.
        # "Spin & Gold" -> source_file começa com "SG"
        # "Tournaments" -> começa com "TM"
        # Para simplificar agora, se pediu torneio, mandamos os sumários
        exprs = []
        if "Spin & Gold" in filters.game_types:
            exprs.append(pl.col("source_file").str.to_lowercase().str.contains("spin&gold"))
        if "Mystery Battle Royale" in filters.game_types:
            exprs.append(pl.col("source_file").str.to_lowercase().str.contains("mystery battle royale") | pl.col("source_file").str.to_lowercase().str.contains("mbr"))
        if "Tournament" in filters.game_types:
            exprs.append(
                (pl.col("source_file").str.to_lowercase().str.contains("tournament") |
                 pl.col("source_file").str.to_lowercase().str.contains("bounty") |
                 pl.col("source_file").str.to_lowercase().str.contains("freeroll") |
                 pl.col("source_file").str.to_lowercase().str.contains("step")) &
                ~pl.col("source_file").str.to_lowercase().str.contains("spin&gold") &
                ~pl.col("source_file").str.to_lowercase().str.contains("mystery battle royale") &
                ~pl.col("source_file").str.to_lowercase().str.contains("mbr")
            )
            
        if exprs:
            combined_expr = exprs[0]
            for e in exprs[1:]:
                combined_expr = combined_expr | e
            df_t = df_t.filter(combined_expr)

    # Adiciona coluna de data baseada no source_file para filtro de data
    if "source_file" in df_t.columns and df_t.height > 0:
        df_t = df_t.with_columns(
            pl.when(pl.col("source_file").str.contains(r"\d{8}"))
              .then(pl.col("source_file").str.extract(r"(\d{8})").str.to_date("%Y%m%d", strict=False))
              .otherwise(None).alias("tourney_date")
        )
        
        if filters.start_date:
            df_t = df_t.filter(pl.col("tourney_date") >= filters.start_date)
        if filters.end_date:
            df_t = df_t.filter(pl.col("tourney_date") <= filters.end_date)

    if filters.search_query:
        sq = filters.search_query.lower()
        if "source_file" in df_t.columns:
            df_t = df_t.filter(pl.col("source_file").str.to_lowercase().str.contains(sq, literal=True))

    return df_t

