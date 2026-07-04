import os
from pathlib import Path
from fastapi import HTTPException
import polars as pl
from .schemas.filters import DashboardFilters

def get_filtered_df(filters: DashboardFilters):
    """
    Carrega o Datalake do usuário sob demanda e aplica os filtros.
    """
    user_id = filters.user_id
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
            # Compatibilidade com parquets antigos sem game_type (Rush & Cash hardcoded)
            df = df.filter(pl.col("hand_id").str.starts_with("RC"))
            
    # Filtro de Nível de Aposta (Stake)
    if filters.stake is not None and "stake_level" in df.columns:
        # Tolerância matemática para floats
        df = df.filter((pl.col("stake_level") - filters.stake).abs() < 0.001)
        
    # Filtro de Plataforma (Novo)
    if filters.platforms and "platform" in df.columns:
        df = df.filter(pl.col("platform").is_in(filters.platforms))

    return df
