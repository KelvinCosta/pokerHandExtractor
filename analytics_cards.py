import polars as pl
from pathlib import Path

def main():
    # Ajuste o caminho se necessário com base na sua máquina
    silver_file = Path("D:/ggpoker/Dados/silver/historico_consolidado.parquet")
    
    print("📥 Carregando o Data Lake (Silver Layer)...")
    df_mãos = pl.read_parquet(silver_file)
    
    # =========================================================================
    # 1. PREPARAÇÃO DOS DADOS (O CRUZAMENTO)
    # =========================================================================
    print("💥 Explodindo as ações e cruzando as cartas...")
    df_actions = (
        df_mãos
        .explode("actions")
        .unnest("actions")
    )
    
    # A MÁGICA: Extrair apenas as cartas do jogador que fez a ação naquela linha.
    # Criamos um struct temporário com o nome do jogador e o dicionário de todas as cartas da mão,
    # e extraímos apenas se a chave bater.
    def extract_player_cards(row):
        p_cards = row.get("player_cards")
        # Se existir o dicionário de cartas e o jogador estiver nele, retorna as cartas
        if isinstance(p_cards, dict):
            return p_cards.get(row.get("player"))
        return None

    df_actions = df_actions.with_columns(
        pl.struct(["player", "player_cards"])
        .map_elements(extract_player_cards, return_dtype=pl.Utf8)
        .alias("cards") # Nova coluna limpa só com as cartas do cara!
    )
    
    # Limpamos a coluna pesada de dicionários da memória, pois já extraímos o que precisávamos
    df_actions = df_actions.drop("player_cards")

    # =========================================================================
    # QUERY 1: COM O QUE ELES GANHAM / PAGAM NO RIVER?
    # O field da NL2 é conhecido por ser "Calling Station" (pagam muito).
    # Vamos ver qual a força da mão dos vilões quando eles dão CALL no River.
    # =========================================================================
    print("\n🕵️ VILÕES QUE PAGAM APOSTAS NO RIVER (E VÃO PRO SHOWDOWN):")
    calls_river = (
        df_actions
        .filter(
            (pl.col("street") == "RIVER") &
            (pl.col("action_type") == "CALLS") &
            (pl.col("player") != "Hero") &     # Exclui você, queremos analisar a população
            (pl.col("cards").is_not_null())    # Apenas mãos onde vimos as cartas deles
        )
        .group_by("cards")
        .agg(pl.len().alias("vezes_que_pagou"))
        .sort("vezes_que_pagou", descending=True)
        .head(10)
    )
    print(calls_river)

    # =========================================================================
    # QUERY 2: COM QUAIS CARTAS ELES DÃO RAISE PRÉ-FLOP?
    # Analisando o range de agressividade da população.
    # =========================================================================
    print("\n🔥 RANGE DE RAISE DOS VILÕES NO PRÉ-FLOP (QUE CHEGARAM NO SHOWDOWN):")
    raises_preflop = (
        df_actions
        .filter(
            (pl.col("street") == "PREFLOP") &
            (pl.col("action_type") == "RAISES") &
            (pl.col("player") != "Hero") &
            (pl.col("cards").is_not_null())
        )
        .group_by("cards")
        .agg(pl.len().alias("frequencia"))
        .sort("frequencia", descending=True)
        .head(10)
    )
    print(raises_preflop)
    
    # =========================================================================
    # BÔNUS: AS SUAS MÃOS MAIS AGRESSIVAS
    # =========================================================================
    print("\n⚔️ SUAS CARTAS MAIS AGRESSIVAS (HERO 3-BET/RAISE PRÉ-FLOP):")
    hero_raises = (
        df_actions
        .filter(
            (pl.col("street") == "PREFLOP") &
            (pl.col("action_type") == "RAISES") &
            (pl.col("player") == "Hero") &
            (pl.col("cards").is_not_null())
        )
        .group_by("cards")
        .agg(pl.len().alias("frequencia"))
        .sort("frequencia", descending=True)
        .head(5)
    )
    print(hero_raises)

if __name__ == "__main__":
    main()