import polars as pl
from pathlib import Path

def main():
    pl.Config.set_tbl_rows(-1)
    
    silver_path = "D:/ggpoker/Dados/silver/*.parquet"
    
    print("📥 Construindo Plano de Execução (Lazy Mode)...")
    lazy_df = pl.scan_parquet(silver_path)
    
    df_maos = lazy_df.collect()

    df_actions_lazy = lazy_df.explode("actions").unnest("actions").collect()
    
    print("🛠️ Materializando os dados em memória (collect)...")
    # 2. Fase de Materialização (Nomes de variáveis distintos impedem o UnboundLocalError)
    df_actions = df_actions_lazy
    
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
    # QUERY 3: AUDITORIA DO PROTOCOLO (Com Data Enrichment)
    # =========================================================================
    print("\n🎯 RELATÓRIO AVANÇADO DE EXTRAÇÃO NO RIVER (Visão 360º):")
    
    # 1. Dimensão Cartas do Hero: Extrai das structs apenas o que o Hero segurava
    hero_cards_df = (
        df_maos
        .select(["hand_id", "player_cards"])
        .explode("player_cards")
        .unnest("player_cards")
        .filter(pl.col("player") == "Hero")
        .select(["hand_id", pl.col("cards").alias("hero_cards")])
    )

    # 2. Dimensão Board: Concatena a lista de cartas da mesa numa única string
    board_df = (
        df_maos
        .select([
            "hand_id", 
            pl.col("board_cards").list.unique(maintain_order=True).list.join(" ").alias("board")
        ])
    )

    # 3. Dimensão Resultado: Quem executou a ação "COLLECT" no final?
    vencedores_df = (
        df_actions
        .filter(pl.col("action_type") == "COLLECT")
        .group_by("hand_id")
        .agg(pl.col("player").alias("lista_vencedores"))
        .with_columns(
            pl.col("lista_vencedores").list.contains("Hero").fill_null(False).alias("hero_ganhou")
        )
    )

    # 4. A Query Matemática (Sizing e Filtros)
    auditoria_base = (
        df_actions
        .filter(
            (pl.col("hand_id").str.starts_with("RC")) & 
            (pl.col("street") == "RIVER")
        )
        .group_by("hand_id")
        .agg(
            pl.col("current_pot").first().alias("pote_final"),
            pl.col("amount").filter(pl.col("action_type").is_in(["BET", "CALL", "RAISE"])).sum().alias("investimento_total_river"),
            pl.col("amount").filter((pl.col("player") == "Hero") & (pl.col("action_type") == "BET")).sum().alias("hero_bet_amount"),
            pl.col("player").filter((pl.col("player") != "Hero") & (pl.col("action_type") == "CALL")).count().alias("qtd_calls_recebidos")
        )
        .filter((pl.col("hero_bet_amount") > 0) & (pl.col("qtd_calls_recebidos") > 0))
        .with_columns((pl.col("pote_final") - pl.col("investimento_total_river")).alias("pote_anterior"))
        .with_columns(((pl.col("hero_bet_amount") / pl.col("pote_anterior")) * 100).round(1).alias("sizing_pct"))
    )

    # 5. O JOIN MESTRE (Consolidação do Data Lake)
    auditoria_final = (
        auditoria_base
        .join(hero_cards_df, on="hand_id", how="left")
        .join(board_df, on="hand_id", how="left")
        .join(vencedores_df, on="hand_id", how="left")
        .with_columns(
            pl.when(pl.col("hero_ganhou") == True).then(pl.lit("✅ GANHOU")).otherwise(pl.lit("❌ PERDEU")).alias("resultado")
        )
        .select([
            "hand_id", "pote_anterior", "hero_bet_amount", "sizing_pct", "hero_cards", "board", "resultado"
        ])
        .sort("sizing_pct", descending=False)
    )

    print(f"Total de potes extraídos analisados: {auditoria_final.height}")
    print(auditoria_final.head(20))

    # =========================================================================
    # 6. MÓDULO FINANCEIRO: CÁLCULO DE EXPECTED VALUE (EV DELTA)
    # Projeta o cenário onde Hero aposta os 75% rigorosamente.
    # =========================================================================
    
    auditoria_ev = (
        auditoria_final
        # A. Calcula qual deveria ter sido o valor ideal da aposta (75% do pote anterior)
        .with_columns(
            (pl.col("pote_anterior") * 0.75).round(2).alias("bet_ideal_75")
        )
        # B. Calcula a diferença em dólares entre o que você apostou e o que deveria ter apostado
        .with_columns(
            (pl.col("bet_ideal_75") - pl.col("hero_bet_amount")).round(2).alias("diferenca_dolares")
        )
        # C. Diagnóstico Lógico do Impacto no Caixa
        .with_columns(
            # Cenário 1: Tinha a melhor mão, mas cobrou barato (Lucro evaporado)
            pl.when((pl.col("resultado") == "✅ GANHOU") & (pl.col("diferenca_dolares") > 0))
            .then(pl.lit("💸 Deixou de ganhar"))
            
            # Cenário 2: Perdeu a mão, mas a preguiça de apostar forte salvou dinheiro
            .when((pl.col("resultado") == "❌ PERDEU") & (pl.col("diferenca_dolares") > 0))
            .then(pl.lit("🛡️ Sorte (Poupou)"))
            
            # Cenário 3: Apostou MAIS que 75% e ganhou (Extração Máxima)
            .when((pl.col("resultado") == "✅ GANHOU") & (pl.col("diferenca_dolares") < 0))
            .then(pl.lit("🔥 Extração Máxima (Overbet)"))
            
            # Cenário 4: Apostou MAIS que 75% e perdeu (Desperdício)
            .when((pl.col("resultado") == "❌ PERDEU") & (pl.col("diferenca_dolares") < 0))
            .then(pl.lit("🩸 Desperdício"))
            
            .otherwise(pl.lit("⚖️ Na Medida"))
            .alias("impacto_no_caixa")
        )
    )

    # print("\n📊 TABELA COM IMPACTO FINANCEIRO (EV DELTA):")
    # print(
    #     auditoria_ev
    #     .select(["hand_id", "resultado", "sizing_pct", "bet_ideal_75", "hero_bet_amount", "impacto_no_caixa"])
    # )

    # 7. Resumo Global de Vazamento (A dor no bolso consolidada)
    lucro_perdido = auditoria_ev.filter(
        (pl.col("resultado") == "✅ GANHOU") & (pl.col("diferenca_dolares") > 0)
    )["diferenca_dolares"].sum()

    dinheiro_salvo = auditoria_ev.filter(
        (pl.col("resultado") == "❌ PERDEU") & (pl.col("diferenca_dolares") > 0)
    )["diferenca_dolares"].sum()

    print(f"\n💰 RESUMO DO CAIXA DO SPRINT ATUAL:")
    print(f"(Aviso: Pressupõe stacks infinitos e que o vilão daria Call nos 75%)")
    print(f"-> 💸 Lucro PERDIDO (Sub-otimização): ${lucro_perdido:.2f}")
    print(f"-> 🛡️ Dinheiro SALVO por sorte (Underbets perdendo): ${dinheiro_salvo:.2f}")
    print(f"-> 📉 BALANÇO REAL DE VAZAMENTO: ${(lucro_perdido - dinheiro_salvo):.2f} dólares deixados na mesa.")

if __name__ == "__main__":
    main()