import polars as pl

def get_hero_cards(df_p):
    """Extrai as cartas do Hero da coluna pré-calculada, mantendo unicidade por mão."""
    return (
        df_p
        .select(["hand_id", "hero_cards"])
        .drop_nulls(subset=["hero_cards"])
        .unique(subset=["hand_id"]) 
    )

def get_board(df_p):
    """Retorna o board pré-calculado em string única por mão."""
    return (
        df_p
        .select(["hand_id", pl.col("board_str").alias("board")])
        .unique(subset=["hand_id"])
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
