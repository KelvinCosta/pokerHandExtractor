import polars as pl
import streamlit as st

def get_hero_cards(df_p):
    """Extrai as cartas do Hero da coluna pré-calculada, mantendo unicidade por mão."""
    return (
        df_p
        .select(["hand_id", "hero_cards"])
        .drop_nulls(subset=["hero_cards"])
        .unique(subset=["hand_id"]) 
    )

def get_board(df_p):
    """Retorna o board pré-calculado em string única por mão, removendo duplicações residuais das streets."""
    return (
        df_p
        .select(["hand_id", "board_str"])
        .drop_nulls(subset=["board_str"])
        .unique(subset=["hand_id"])
        .with_columns(
            pl.col("board_str")
            .str.split(" ")
            .list.unique(maintain_order=True)
            .list.join(" ")
            .alias("board")
        )
        .select(["hand_id", "board"])
    )

def get_viloes_cached(df_p):
    """Extrai os IDs dos jogadores (exceto Hero) nas mãos válidas."""
    return (
        df_p.filter(
            (pl.col("player") != "Hero") & 
            (pl.col("hand_id").str.starts_with("RC"))
        )
        .select(["hand_id", "player"])
        .unique() 
    )

def get_vencedores_df(df_p):
    """Retorna a lista de vencedores e a flag se o Hero ganhou, já pré-calculadas na base."""
    return (
        df_p
        .select(["hand_id", "lista_vencedores", "hero_ganhou"])
        .unique(subset=["hand_id"])
    )

def process_hand_data(player_cards_list, player):
    """
    Transforma uma lista de dicionários de cartas no formato canônico da mão (ex: 'AKs', 'AA').
    Adaptado do script de analytics.
    """
    if not isinstance(player_cards_list, list) or not player:
        return {"combo": None, "hand_canonical": None}
        
    raw_combo = None
    for item in player_cards_list:
        if item and item.get("player") == player:
            raw_combo = item.get("cards")
            break
            
    if not raw_combo:
        return {"combo": None, "hand_canonical": None}
        
    cards = raw_combo.replace("[", "").replace("]", "").strip().split()
    if len(cards) != 2:
        return {"combo": None, "hand_canonical": None}
        
    # ORDENAÇÃO OFICIAL DE POKER
    ranks = "23456789TJQKA"
    cards.sort(key=lambda c: (-ranks.index(c[0]) if c[0] in ranks else 0, c[1]))
    
    combo_str = f"{cards[0]} {cards[1]}"
    
    # GERAÇÃO DA CANÔNICA
    v1, s1 = cards[0][0], cards[0][1]
    v2, s2 = cards[1][0], cards[1][1]
    
    if v1 == v2:
        canonical = f"{v1}{v2}"  # Par (Ex: AA)
    elif s1 == s2:
        canonical = f"{v1}{v2}s" # Suited (Ex: AKs)
    else:
        canonical = f"{v1}{v2}o" # Offsuit (Ex: AKo)
        
    return {"combo": combo_str, "hand_canonical": canonical}

def get_villains_cards_shown(df_p):
    """Extrai as cartas reveladas pelos vilões no showdown e junta numa string única por mão."""
    return (
        df_p
        .select(["hand_id", "player_cards"])
        .drop_nulls("player_cards")
        .unique("hand_id")
        .explode("player_cards")
        .drop_nulls("player_cards")
        .filter(pl.col("player_cards").struct.field("player") != "Hero")
        .with_columns(
            pl.format("{}: {}", 
                      pl.col("player_cards").struct.field("player"), 
                      pl.col("player_cards").struct.field("cards")).alias("villain_show")
        )
        .group_by("hand_id")
        .agg(pl.col("villain_show").str.join(" | ").alias("villains_cards"))
    )

def get_player_positions_df(df_p):
    """Mapeia a posição de cada jogador na mão baseado na ordem de ação pré-flop."""
    # Extrai a ordem de ação no preflop (SB e BB postam primeiro)
    ordem_df = (
        df_p
        .filter(pl.col("street") == "PRE_FLOP")
        .select(["hand_id", "player"])
        .unique(subset=["hand_id", "player"], maintain_order=True)
        .group_by("hand_id", maintain_order=True)
        .agg(pl.col("player").alias("players_order"))
    )
    
    def map_positions(players):
        n = len(players)
        if n == 2: return ["SB", "BB"]
        elif n == 3: return ["SB", "BB", "BTN"]
        elif n == 4: return ["SB", "BB", "CO", "BTN"]
        elif n == 5: return ["SB", "BB", "UTG", "CO", "BTN"]
        elif n == 6: return ["SB", "BB", "UTG", "MP", "CO", "BTN"]
        else: return ["UNK"] * n
        
    return (
        ordem_df.with_columns(
            pl.col("players_order").map_elements(map_positions, return_dtype=pl.List(pl.Utf8)).alias("position")
        )
        .explode(["players_order", "position"])
        .rename({"players_order": "player"})
        .select(["hand_id", "player", "position"])
    )

@st.cache_data
def get_known_cards_df(df_p):
    """Gera um DataFrame com as cartas canônicas conhecidas dos vilões no showdown."""
    return (
        df_p.filter((pl.col("player") != "Hero") & (pl.col("player_cards").is_not_null()))
        .with_columns(
            pl.struct(["player_cards", "player"])
            .map_elements(lambda x: process_hand_data(x["player_cards"], x["player"]), return_dtype=pl.Struct({"combo": pl.Utf8, "hand_canonical": pl.Utf8}))
            .alias("cards_info")
        )
        .unnest("cards_info")
        .filter(pl.col("hand_canonical").is_not_null())
    )
