import polars as pl
from pathlib import Path

def process_hand_data(row):
    player = row.get("player")
    p_cards = row.get("player_cards")
    
    # Se não tem cartas para esse jogador, retorna nulo para as duas features
    if not isinstance(p_cards, dict) or not player:
        return {"combo": None, "hand_canonical": None}
        
    raw_combo = p_cards.get(player)
    if not raw_combo:
        return {"combo": None, "hand_canonical": None}
        
    # 1. Separa as cartas (Ex: "[Ac Ah]" -> ["Ac", "Ah"])
    cards = raw_combo.replace("[", "").replace("]", "").strip().split()
    if len(cards) != 2:
        return {"combo": None, "hand_canonical": None}
        
    # 2. ORDENAÇÃO OFICIAL DE POKER
    ranks = "23456789TJQKA"
    # O sinal de menos (-) garante que A (índice 12) venha antes de K (índice 11)
    cards.sort(key=lambda c: (-ranks.index(c[0]) if c[0] in ranks else 0, c[1]))
    
    combo_str = f"{cards[0]} {cards[1]}"
    
    # 3. GERAÇÃO DA CANÔNICA
    v1, s1 = cards[0][0], cards[0][1]
    v2, s2 = cards[1][0], cards[1][1]
    
    if v1 == v2:
        canonical = f"{v1}{v2}"  # Par (Ex: AA)
    elif s1 == s2:
        canonical = f"{v1}{v2}s" # Suited (Ex: AKs)
    else:
        canonical = f"{v1}{v2}o" # Offsuit (Ex: AKo)
        
    return {"combo": combo_str, "hand_canonical": canonical}

def main():
    # Para não cortar as linhas no terminal
    pl.Config.set_tbl_rows(-1)
    
    silver_file = Path("D:/ggpoker/Dados/silver/historico_consolidado.parquet")
    print("📥 Carregando Silver Layer...")
    df_mãos = pl.read_parquet(silver_file)
    
    # Explode a lista de ações
    df_actions = df_mãos.explode("actions").unnest("actions")

    print("🛠️ Processando cartas (Extração, Ordenação por Força e Canônica)...")
    # NATIVE POLARS WAY: Uma única passagem mapeando para um Struct (Dicionário)
    df_actions = df_actions.with_columns(
        pl.struct(["player", "player_cards"])
        .map_elements(process_hand_data, return_dtype=pl.Struct({"combo": pl.Utf8, "hand_canonical": pl.Utf8}))
        .alias("cards_info")
    ).unnest("cards_info").drop("player_cards")

    # ---------------------------------------------------------
    # QUERY 1: O QUE ELES REALMENTE TÊM NO RIVER?
    # ---------------------------------------------------------
    print("\n🔍 MÃOS (CANÔNICAS) QUE PAGAM NO RIVER:")
    river_calls = (
        df_actions
        .filter(
            (pl.col("street") == "RIVER") & 
            (pl.col("action_type") == "CALLS") &
            (pl.col("player") != "Hero") &
            (pl.col("hand_canonical").is_not_null())
        )
        .group_by("hand_canonical")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    # Mostra só um preview no terminal, para não travar a sua leitura
    print(river_calls.head(10)) 
    
    csv_path = "D:/ggpoker/Dados/gold/chamadas_river.csv"
    river_calls.write_csv(csv_path)
    print(f"\n💾 Relatório COMPLETO das chamadas no River exportado para: {csv_path}")

    # ---------------------------------------------------------
    # QUERY 2: DETALHAMENTO DE UM COMBO ESPECÍFICO (Ex: AA)
    # ---------------------------------------------------------
    print("\n💎 DETALHAMENTO DOS COMBOS DE 'AA' DA POPULAÇÃO:")
    aa_details = (
        df_actions
        .filter(pl.col("hand_canonical") == "AA")
        .group_by("combo")
        .agg(pl.len().alias("vezes_visto"))
        .sort("combo") # Organiza alfabeticamente a tabela de visualização
    )
    print(aa_details)

    print("\n🔍 TOP 20 MÃOS GERAIS DA POPULAÇÃO (SHOWDOWN RANGE):")
    todas_as_maos = (
        df_actions
        .filter(
            (pl.col("player") != "Hero") &
            (pl.col("hand_canonical").is_not_null())
        )
        .group_by("hand_canonical")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print(todas_as_maos.head(20))
    csv_path = "D:/ggpoker/Dados/gold/todas_as_maos.csv"
    todas_as_maos.write_csv(csv_path)   
if __name__ == "__main__":
    main()