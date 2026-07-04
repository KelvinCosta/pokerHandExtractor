import streamlit as st
import polars as pl

def render_overview(df):
    st.subheader("Distribuição de Ações")
    dist_df = df.group_by("action_type").agg(pl.len())
    st.bar_chart(dist_df.to_pandas(), x="action_type", y="len")
