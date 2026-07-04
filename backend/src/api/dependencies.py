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


def get_filtered_df(filters: DashboardFilters, user: User):
    """
    Carrega o Datalake do usuário sob demanda e aplica os filtros.
    """
    user_id = user.id
    silver_dir = Path(os.getenv("DATALAKE_SILVER", "./datalake/silver")) / user_id

    
    if not silver_dir.exists():
        # Se não há pasta pro usuário, retorna um DF vazio com esquema base
        return pl.DataFrame(schema={"hand_id": pl.Utf8, "platform": pl.Utf8})
        
    try:
        df = pl.scan_parquet(str(silver_dir / "hands_part_*.parquet")).collect()
        df = df.unique(subset=["hand_id"], keep="last", maintain_order=True)
        df = df.explode("actions").unnest("actions")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler o datalake: {e}")

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
