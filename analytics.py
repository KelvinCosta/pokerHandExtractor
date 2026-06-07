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
    # Exclusivo para Rush & Cash (RnC)
    # =========================================================================
    print("\n🎯 RELATÓRIO DE EXTRAÇÃO NO RIVER (Hero BET -> Villain CALL) - APENAS RUSH & CASH:")
    
    auditoria_river = (
        df_actions
        # 1. Segregação de Dados: Apenas Cash Game (RC) e na aba do River
        .filter(
            (pl.col("hand_id").str.starts_with("RC")) & 
            (pl.col("street") == "RIVER")
        )
        .group_by("hand_id")
        .agg(
            # O pote final consolidado
            pl.col("current_pot").first().alias("pote_final"),
            
            # A soma de todo o capital injectado na mesa apenas no River
            pl.col("amount").filter(
                pl.col("action_type").is_in(["BET", "CALL", "RAISE"])
            ).sum().alias("investimento_total_river"),
            
            # O isolamento da sua aposta
            pl.col("amount").filter(
                (pl.col("player") == "Hero") & 
                (pl.col("action_type") == "BET")
            ).sum().alias("hero_bet_amount"),
            
            # O contador de pagamentos de terceiros
            pl.col("player").filter(
                (pl.col("player") != "Hero") & 
                (pl.col("action_type") == "CALL")
            ).count().alias("qtd_calls_recebidos")
        )
        # 2. Mantém estritamente as instâncias de sucesso (Bet e Call)
        .filter(
            (pl.col("hero_bet_amount") > 0) & 
            (pl.col("qtd_calls_recebidos") > 0)
        )
        # 3. Feature Engineering: Cálculo dinâmico em memória
        .with_columns(
            (pl.col("pote_final") - pl.col("investimento_total_river")).alias("pote_anterior")
        )
        .with_columns(
            ((pl.col("hero_bet_amount") / pl.col("pote_anterior")) * 100).round(1).alias("sizing_pct")
        )
        # 4. Ordenação Crítica: Traz as falhas de protocolo (menores percentagens) para o topo
        .sort("sizing_pct", descending=False)
    )
    
    print(f"Total de potes extraídos no River (Rush & Cash): {auditoria_river.height}")
    print("\nDetalhamento dos Dimensionamentos Aplicados (Do Pior para o Melhor):")
    # Mostra um ecrã limpo com o ID da mão para revisão manual posterior
    print(auditoria_river.select(["hand_id", "pote_anterior", "hero_bet_amount", "sizing_pct"]).head(15))

if __name__ == "__main__":
    main()