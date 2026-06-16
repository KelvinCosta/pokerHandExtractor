import streamlit as st
import polars as pl
from .config import DATALAKE_SILVER

@st.cache_data
def load_data():
    df = pl.scan_parquet(DATALAKE_SILVER / "*.parquet").collect()
    df_gold = df.explode("actions").unnest("actions")
    return df_gold

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
