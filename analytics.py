import polars as pl
from pathlib import Path

def main():
    # Remove limite de linhas no console para relatórios
    pl.Config.set_tbl_rows(-1)
    
    silver_path = "D:/ggpoker/Dados/silver/*.parquet"
    
    print("📥 Construindo Plano de Execução (Lazy Mode)...")
    lazy_df = pl.scan_parquet(silver_path)
    
    # 1. Fase Preguiçosa (Sem uso de RAM)
    df_actions_lazy = lazy_df.explode("actions").unnest("actions")
    
    print("🛠️ Materializando os dados em memória (collect)...")
    # 2. Fase de Materialização (Nomes de variáveis distintos impedem o UnboundLocalError)
    df_actions = df_actions_lazy.collect()
    
    print(f"✅ Mãos únicas processadas: {df_actions.select('hand_id').n_unique()}")
    print(f"✅ Ações individuais em memória: {df_actions.height}\n")

    # =========================================================================
    # QUERY 1: ANÁLISE DE POPULAÇÃO (MDA)
    # =========================================================================
    print("🔥 TOP 5 JOGADORES MAIS AGRESSIVOS (Frequência Bruta de 'RAISE'):")
    top_agressores = (
        df_actions
        .filter(pl.col("action_type") == "RAISE") # Filtro normalizado
        .group_by("player")
        .agg(pl.len().alias("total_raises"))
        .sort("total_raises", descending=True)
        .head(5)
    )
    print(top_agressores)

    # =========================================================================
    # QUERY 2: ESTATÍSTICA MACRO DA NL2
    # =========================================================================
    print("\n📊 DISTRIBUIÇÃO GLOBAL DE AÇÕES DA POPULAÇÃO DA NL2:")
    distribuicao_acoes = (
        df_actions
        .group_by("action_type")
        .agg(pl.len().alias("ocorrencias"))
        .sort("ocorrencias", descending=True)
    )
    print(distribuicao_acoes)

    # =========================================================================
    # QUERY 3: AUDITORIA DO PROTOCOLO (Sizing de 75% no River)
    # Filtra mãos exatas onde Hero apostou por valor no River e o vilão pagou
    # =========================================================================
    print("\n🎯 RELATÓRIO DE EXTRAÇÃO NO RIVER (Hero BET -> Villain CALL):")
    
    auditoria_river = (
        df_actions
        .filter(pl.col("street") == "RIVER")
        .group_by("hand_id")
        .agg(
            pl.col("current_pot").first().alias("pote_final"),
            # Isola apenas a aposta do Hero na rua
            pl.col("amount").filter(
                (pl.col("player") == "Hero") & 
                (pl.col("action_type") == "BET")
            ).sum().alias("hero_bet_amount"),
            # Isola e conta se houve pagamento de terceiros
            pl.col("player").filter(
                (pl.col("player") != "Hero") & 
                (pl.col("action_type") == "CALL")
            ).count().alias("qtd_calls_recebidos")
        )
        # Retorna estritamente as instâncias que satisfazem a regra do deploy
        .filter(
            (pl.col("hero_bet_amount") > 0) & 
            (pl.col("qtd_calls_recebidos") > 0)
        )
        .sort("pote_final", descending=True)
    )
    
    print(f"Total de potes extraídos no River sob essas condições: {auditoria_river.height}")
    print("\nTop 10 Maiores Potes Extraídos:")
    print(auditoria_river.head(10))

if __name__ == "__main__":
    main()