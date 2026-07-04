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

_DATALAKE_CACHE = {}  # { user_id: {"df": pl.DataFrame, "timestamp": float} }

def invalidate_cache(user_id: str):
    """Limpa o cache do Datalake em memória para o usuário (chamado após o ETL)"""
    if user_id in _DATALAKE_CACHE:
        del _DATALAKE_CACHE[user_id]

def get_filtered_df(filters: DashboardFilters, user: User):
    """
    Carrega o Datalake do usuário sob demanda (usando Cache Global) e aplica os filtros.
    """
    user_id = user.id
    silver_bucket = os.getenv("S3_SILVER_BUCKET", "poker-silver")
    
    # Usar Cache em Memória (Evita I/O e Explode massivo a cada request)
    if user_id in _DATALAKE_CACHE:
        df = _DATALAKE_CACHE[user_id]["df"]
    else:
        try:
            # Opções de conexão com MinIO / S3 Compatível
            storage_options = {
                "endpoint_url": os.getenv("S3_ENDPOINT_URL", "http://localhost:9000"),
                "aws_access_key_id": os.getenv("S3_ACCESS_KEY", "admin"),
                "aws_secret_access_key": os.getenv("S3_SECRET_KEY", "password123"),
                "aws_region": "us-east-1"
            }
            
            s3_path = f"s3://{silver_bucket}/{user_id}/hands_part_*.parquet"
            
            # Testa se há arquivos no S3 para aquele usuário antes de escanear (evita erro se não houver dados)
            from src.core.storage import get_s3_client
            s3 = get_s3_client()
            response = s3.list_objects_v2(Bucket=silver_bucket, Prefix=f"{user_id}/hands_part_")
            
            if "Contents" not in response:
                # Se não há parquets, retorna um DF vazio com esquema base
                return pl.DataFrame(schema={"hand_id": pl.Utf8, "platform": pl.Utf8})

            df = pl.scan_parquet(s3_path, storage_options=storage_options).collect()
            df = df.unique(subset=["hand_id"], keep="last", maintain_order=True)
            df = df.explode("actions").unnest("actions")
            _DATALAKE_CACHE[user_id] = {"df": df, "timestamp": time.time()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler o datalake do S3: {e}")

    # Verifica se há coluna de data
    nome_coluna_data = "date" if "date" in df.columns else "timestamp" if "timestamp" in df.columns else None
    
    if nome_coluna_data:
        # Tenta padronizar os nomes de colunas como o Streamlit fazia
        df = df.with_columns(
            pl.col(nome_coluna_data)
            .str.to_datetime("%Y/%m/%d %H:%M:%S", strict=False)
            .dt.date()
            .alias("data_limpa")
        )
        
        # Filtro de Data
        if filters.start_date:
            df = df.filter(pl.col("data_limpa") >= filters.start_date)
        if filters.end_date:
            df = df.filter(pl.col("data_limpa") <= filters.end_date)
            
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
        # Tolerância matemática para floats
        df = df.filter((pl.col("stake_level") - filters.stake).abs() < 0.001)
        
    # Filtro de Plataforma (Novo)
    if filters.platforms and "platform" in df.columns:
        df = df.filter(pl.col("platform").is_in(filters.platforms))

    return df
