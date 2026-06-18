import polars as pl

def get_hero_cards(df_p):
    """Extrai as cartas do Hero da coluna struct explodida, mantendo unicidade por mão."""
    return (
        df_p
        .select(["hand_id", "player_cards"])
        .drop_nulls(subset=["player_cards"])
        .unique(subset=["hand_id"]) 
        .explode("player_cards")
        .unnest("player_cards")
        .filter(pl.col("player") == "Hero")
        .select(["hand_id", pl.col("cards").alias("hero_cards")])
    )

def get_board(df_p):
    """Agrega as cartas comunitárias do board numa string única por mão."""
    return (
        df_p
        .select(["hand_id", "board_cards"])
        .drop_nulls(subset=["board_cards"])
        .unique(subset=["hand_id"])
        .with_columns(
            pl.col("board_cards").list.unique(maintain_order=True).list.join(" ").alias("board")
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
    """Retorna uma lista de vencedores por mão e a flag booleana se o Hero ganhou a mão."""
    return (
        df_p.filter(pl.col("action_type") == "COLLECT")
        .group_by("hand_id")
        .agg(pl.col("player").unique().alias("lista_vencedores"))
        .with_columns(
            pl.col("lista_vencedores").list.contains("Hero").fill_null(False).alias("hero_ganhou")
        )
    )
