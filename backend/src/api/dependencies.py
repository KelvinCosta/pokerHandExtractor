from fastapi import HTTPException
import polars as pl
from .schemas.filters import DashboardFilters
from .main import AppState

def get_filtered_df(filters: DashboardFilters):
    """
    Função injetada nas rotas para retornar o DataFrame filtrado 
    (Substitui o papel do render_sidebar do Streamlit).
    """
    df = AppState.df_hands
    
    if df is None:
        raise HTTPException(status_code=503, detail="Datalake não carregado em memória.")

    # Verifica se há coluna de data
    nome_coluna_data = "date" if "date" in df.columns else "timestamp" if "timestamp" in df.columns else None
    
    if nome_coluna_data:
        # Tenta padronizar os nomes de colunas como o Streamlit fazia
        df = df.with_columns(
            pl.col(nome_coluna_data).cast(pl.Date).alias("data_limpa")
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

    return df
