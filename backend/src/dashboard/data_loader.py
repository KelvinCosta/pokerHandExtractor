import streamlit as st
import polars as pl
from .config import DATALAKE_SILVER

@st.cache_data
def load_data():
    path_str = str(DATALAKE_SILVER / "hands_part_*.parquet").replace("\\", "/")
    df = pl.scan_parquet(path_str).collect()
    
    # Previne dados duplicados caso o usuário não delete os parquets antigos ao re-extrair
    df = df.unique(subset=["hand_id"], keep="last", maintain_order=True)
    
    df_gold = df.explode("actions").unnest("actions")
    return df_gold

@st.cache_data
def load_tournaments():
    try:
        df = pl.read_parquet(DATALAKE_SILVER / "tournaments.parquet")
        return df
    except Exception:
        # Se o arquivo ainda não existir, retorna df vazio com as colunas esperadas
        return pl.DataFrame(schema={"tournament_id": pl.Utf8, "buy_in": pl.Float64, "prize": pl.Float64, "source_file": pl.Utf8})

def get_base_dataframe():
    df = load_data()
    
    nome_coluna_data = "date" if "date" in df.columns else "timestamp" if "timestamp" in df.columns else None
    
    if nome_coluna_data:
        df = df.with_columns(
            pl.col(nome_coluna_data)
            .str.to_datetime("%Y/%m/%d %H:%M:%S", strict=False)
            .dt.date() 
            .alias("data_limpa")
        )
        
    return df, nome_coluna_data
