import streamlit as st
import polars as pl

def render_rivalry(df, df_viloes, df_tags):
    st.divider()
    st.subheader("⚔️ Ranking de Rivalidade (ATMs vs Nemesis)")

    df_hero_investido = (
        df.filter(
            (pl.col("player") == "Hero") & 
            (pl.col("action_type").is_in(["SMALL BLIND", "BIG BLIND", "POST", "BET", "CALL", "RAISE"]))
        )
        .group_by("hand_id")
        .agg(pl.col("amount").sum().alias("hero_colocou"))
    )

    df_hero_ganhou = (
        df.filter((pl.col("player") == "Hero") & (pl.col("action_type") == "COLLECT"))
        .group_by("hand_id")
        .agg(pl.col("amount").sum().alias("hero_puxou"))
    )

    df_hero_pnl = (
        df.select("hand_id").unique()
        .join(df_hero_investido, on="hand_id", how="left")
        .join(df_hero_ganhou, on="hand_id", how="left")
        .fill_null(0.0) 
        .with_columns(
            (pl.col("hero_puxou") - pl.col("hero_colocou")).round(2).alias("lucro_liquido_hero")
        )
    )

    if not df_tags.is_empty():
        df_confrontos = (
            df_viloes.join(df_tags, on="player", how="inner") 
            .join(df_hero_pnl, on="hand_id", how="inner")
            .group_by(["player", "notas_vilao"])
            .agg(
                pl.col("lucro_liquido_hero").sum().round(2).alias("saldo_financeiro"),
                pl.col("hand_id").count().alias("potes_disputados")
            )
            .with_columns(
                pl.when(pl.col("saldo_financeiro") > 0).then(pl.lit("💰 ATM"))
                .when(pl.col("saldo_financeiro") < 0).then(pl.lit("💀 Nemesis"))
                .otherwise(pl.lit("⚖️ Break-even")).alias("classificacao")
            )
        )

        col_atm, col_nemesis = st.columns(2)

        with col_atm:
            st.success("💰 Os seus ATMs (Lucro Máximo Extraído)")
            df_atms = df_confrontos.filter(pl.col("saldo_financeiro") > 0).sort("saldo_financeiro", descending=True)
            st.dataframe(df_atms.to_pandas(), use_container_width=True, hide_index=True)

        with col_nemesis:
            st.error("💀 As suas Nemesis (Vazamento Máximo)")
            df_nems = df_confrontos.filter(pl.col("saldo_financeiro") < 0).sort("saldo_financeiro", descending=False)
            st.dataframe(df_nems.to_pandas(), use_container_width=True, hide_index=True)
            
    else:
        st.info("O painel de rivalidade será ativado assim que gravar a primeira anotação num vilão.")
