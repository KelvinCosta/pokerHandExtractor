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

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


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
            
    # Filtro de Busca Textual (ID da mão ou Oponentes)
    if filters.search_query:
        sq = filters.search_query.lower()
        if "player" in df.columns:
            # Encontra os hand_ids que tem match com a busca
            matching_hands = df.filter(
                pl.col("hand_id").str.to_lowercase().str.contains(sq) | 
                pl.col("player").str.to_lowercase().str.contains(sq)
            ).select("hand_id").unique()
            
            # Mantém todas as ações dessas mãos intactas
            df = df.join(matching_hands, on="hand_id", how="inner")
        else:
            df = df.filter(pl.col("hand_id").str.to_lowercase().str.contains(sq))
            
    # Filtro Dinâmico de Tipo de Jogo
    if filters.game_types:
        if "game_type" in df.columns:
            df = df.filter(pl.col("game_type").is_in(filters.game_types))
        else:
            # Fallback provisório baseado no prefixo do hand_id
            exprs = []
            if "Rush & Cash" in filters.game_types:
                exprs.append(pl.col("hand_id").str.starts_with("RC"))
            if "Tournaments" in filters.game_types:
                exprs.append(pl.col("hand_id").str.starts_with("SG") | pl.col("hand_id").str.starts_with("TM"))
            if "Regular" in filters.game_types:
                exprs.append(pl.col("hand_id").str.starts_with("HD"))
            
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
    if filters.stake is not None and "stake_level" in df.columns:
        df = df.filter((pl.col("stake_level") - filters.stake).abs() < 0.001)
        
    # Filtro de Plataforma (Novo)
    if filters.platforms and "platform" in df.columns:
        df = df.filter(pl.col("platform").is_in(filters.platforms))

    return df

def _load_user_datalake(user_id: str, silver_bucket: str) -> dict:
    # Fast path sem lock
    if user_id in _DATALAKE_CACHE:
        return _DATALAKE_CACHE[user_id]
        
    with _CACHE_LOCK:
        # Double-check locking pattern
        if user_id in _DATALAKE_CACHE:
            return _DATALAKE_CACHE[user_id]

        try:
            storage_options = {
                "endpoint_url": os.getenv("S3_ENDPOINT_URL", "http://localhost:9000"),
                "aws_access_key_id": os.getenv("S3_ACCESS_KEY", "admin"),
                "aws_secret_access_key": os.getenv("S3_SECRET_KEY", "password123"),
                "aws_region": "us-east-1"
            }
            
            s3_path = f"s3://{silver_bucket}/{user_id}/hands_part_*.parquet"
            from src.core.storage import get_s3_client
            s3 = get_s3_client()
            response = s3.list_objects_v2(Bucket=silver_bucket, Prefix=f"{user_id}/hands_part_")
            
            if "Contents" not in response:
                empty_df = pl.DataFrame(schema={"hand_id": pl.Utf8, "platform": pl.Utf8})
                cache_entry = {"df_hands": empty_df, "df_actions": empty_df, "timestamp": time.time()}
                _DATALAKE_CACHE[user_id] = cache_entry
                return cache_entry

            df_hands = pl.scan_parquet(s3_path, storage_options=storage_options).collect()
            df_hands = df_hands.unique(subset=["hand_id"], keep="last", maintain_order=True)

            nome_coluna_data = "date" if "date" in df_hands.columns else "timestamp" if "timestamp" in df_hands.columns else None
            if nome_coluna_data:
                df_hands = df_hands.with_columns(
                    pl.col(nome_coluna_data).str.to_datetime("%Y/%m/%d %H:%M:%S", strict=False).dt.date().alias("data_limpa")
                )
                
            # TODO: Filtro removido (Milestone 6) - O ETL agora separa hero_net_profit_usd de hero_net_chips corretamente
            # if "game_type" in df_hands.columns:
            #     df_hands = df_hands.filter(
            #         ~pl.col("game_type").is_in(["Tournament", "Spin & Gold", "Mystery Battle Royale"])
            #     )

            df_actions = df_hands.explode("actions").unnest("actions")
            
            # Carregar sumários de torneios se existirem
            df_tournaments = pl.DataFrame()
            try:
                s3_tournaments_path = f"s3://{silver_bucket}/{user_id}/tournaments.parquet"
                df_tournaments = pl.scan_parquet(s3_tournaments_path, storage_options=storage_options).collect()
            except Exception:
                pass # Se não houver arquivo de torneios, segue normalmente com df vazio
            
            cache_entry = {"df_hands": df_hands, "df_actions": df_actions, "df_tournaments": df_tournaments, "timestamp": time.time()}
            _DATALAKE_CACHE[user_id] = cache_entry
            return cache_entry
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler o datalake do S3: {e}")

def get_filtered_df(filters: DashboardFilters, user: User) -> pl.DataFrame:
    """Retorna o Datalake EXPLODIDO no nível da Ação (usado por Analytics/Postflop/BigPots)"""
    silver_bucket = os.getenv("S3_SILVER_BUCKET", "poker-silver")
    cache_entry = _load_user_datalake(user.id, silver_bucket)
    return _apply_filters(cache_entry["df_actions"], filters)

def get_filtered_hands_df(filters: DashboardFilters, user: User) -> pl.DataFrame:
    """Retorna o Datalake base SEM explodir (Otimizado! Usado por Health/Preflop/Trend)"""
    silver_bucket = os.getenv("S3_SILVER_BUCKET", "poker-silver")
    cache_entry = _load_user_datalake(user.id, silver_bucket)
    return _apply_filters(cache_entry["df_hands"], filters)

def get_filtered_tournaments_df(filters: DashboardFilters, user: User) -> pl.DataFrame:
    """Retorna os Sumários de Torneios filtrados (usado para compor o Profit total)"""
    silver_bucket = os.getenv("S3_SILVER_BUCKET", "poker-silver")
    cache_entry = _load_user_datalake(user.id, silver_bucket)
    df_t = cache_entry.get("df_tournaments", pl.DataFrame())
    
    if df_t.height == 0:
        return df_t
        
    if filters.game_types:
        # Verifica se algum dos tipos selecionados é de torneio
        tournament_types = ["Tournaments", "Spin & Gold", "Mystery Battle Royale"]
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
            exprs.append(pl.col("source_file").str.starts_with("SG"))
        if "Tournaments" in filters.game_types:
            exprs.append(pl.col("source_file").str.starts_with("TM"))
            
        if exprs:
            combined_expr = exprs[0]
            for e in exprs[1:]:
                combined_expr = combined_expr | e
            df_t = df_t.filter(combined_expr)

    return df_t

