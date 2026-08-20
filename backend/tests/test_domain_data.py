import pytest
import sys
import os
import polars as pl

# Adiciona a raiz do projeto ao path do Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.dashboard.domain_data import (
    get_hero_cards,
    get_board,
    get_viloes_cached,
    get_vencedores_df,
    process_hand_data,
    get_villains_cards_shown,
    get_player_positions_df
)

def test_get_hero_cards():
    df = pl.DataFrame({
        "hand_id": ["1", "2", "3", "3"],
        "hero_cards": ["Ah Kh", None, "2s 2c", "2s 2c"]
    })
    res = get_hero_cards(df)
    
    assert res.height == 2
    assert "hand_id" in res.columns
    assert "hero_cards" in res.columns
    
    hero_cards_map = dict(zip(res["hand_id"].to_list(), res["hero_cards"].to_list()))
    assert hero_cards_map["1"] == "Ah Kh"
    assert hero_cards_map["3"] == "2s 2c"

def test_get_board():
    df = pl.DataFrame({
        "hand_id": ["1", "1", "2"],
        "board_str": ["Ah Kh Qh", "Ah Kh Qh Jh", None]
    })
    res = get_board(df)
    
    assert res.height == 1
    assert "hand_id" in res.columns
    assert "board" in res.columns
    
    # O unique(subset=["hand_id"]) do Polars vai pegar a primeira ocorrência (Ah Kh Qh)
    board_result = res.filter(pl.col("hand_id") == "1")["board"][0]
    
    assert "Ah" in board_result
    assert "Jh" not in board_result # Jh foi ignorado pois pertencia à segunda ocorrência duplicada

def test_get_viloes_cached():
    df = pl.DataFrame({
        "hand_id": ["RC1", "RC1", "RC2", "XX1"], # XX1 não deve ser aceito
        "player": ["Hero", "Villain1", "Villain2", "Villain3"]
    })
    res = get_viloes_cached(df)
    
    assert res.height == 2
    players = res["player"].to_list()
    assert "Hero" not in players
    assert "Villain1" in players
    assert "Villain2" in players
    assert "Villain3" not in players

def test_get_vencedores_df():
    df = pl.DataFrame({
        "hand_id": ["1", "1", "2"],
        "lista_vencedores": [["Hero"], ["Hero"], ["Villain"]],
        "hero_ganhou": [True, True, False]
    })
    res = get_vencedores_df(df)
    
    assert res.height == 2
    vencedores_map = dict(zip(res["hand_id"].to_list(), res["hero_ganhou"].to_list()))
    assert vencedores_map["1"] is True
    assert vencedores_map["2"] is False

def test_process_hand_data():
    # Testa Pocket Pair (Par)
    res_pair = process_hand_data([{"player": "Hero", "cards": "[As Ah]"}], "Hero")
    assert res_pair["hand_canonical"] == "AA"
    # Ah As, pois ambos tem rank A, mas 'h' (hearts) vem antes de 's' (spades) alfabeticamente
    assert res_pair["combo"] == "Ah As"
    
    # Testa Suited (Naipe igual, ex: Espadas/Spades)
    res_suited = process_hand_data([{"player": "V1", "cards": "[Ks Qs]"}], "V1")
    assert res_suited["hand_canonical"] == "KQs"
    
    # Testa Offsuit (Naipes diferentes) e Ordenação (Carta de maior Rank sempre vem primeiro)
    res_offsuit = process_hand_data([{"player": "V1", "cards": "[2h Ad]"}], "V1")
    assert res_offsuit["hand_canonical"] == "A2o"
    
    # Testa Offsuit sem colchetes 
    res_offsuit2 = process_hand_data([{"player": "V1", "cards": "Jd Tc"}], "V1")
    assert res_offsuit2["hand_canonical"] == "JTo"
    
    # Testa retornos vazios/inválidos
    assert process_hand_data(None, "V1")["hand_canonical"] is None
    assert process_hand_data([], "V1")["hand_canonical"] is None
    assert process_hand_data([{"player": "V2", "cards": "As"}], "V1")["hand_canonical"] is None # Jogador não existe
    assert process_hand_data([{"player": "V1", "cards": "As"}], "V1")["hand_canonical"] is None # Faltando carta (len != 2)

def test_get_villains_cards_shown():
    df = pl.DataFrame({
        "hand_id": ["1", "2"],
        "player_cards": [
            [{"player": "Hero", "cards": "Ah Kh"}, {"player": "V1", "cards": "2s 2c"}],
            [{"player": "V2", "cards": "Qs Qd"}, {"player": "V3", "cards": "Js Jc"}]
        ]
    })
    res = get_villains_cards_shown(df)
    
    assert res.height == 2
    res_map = dict(zip(res["hand_id"].to_list(), res["villains_cards"].to_list()))
    assert res_map["1"] == "V1: 2s 2c"
    # A mão 2 tem dois vilões que mostram cartas, devem ser separados por |
    assert "V2: Qs Qd" in res_map["2"]
    assert "V3: Js Jc" in res_map["2"]
    assert "|" in res_map["2"]

def test_get_player_positions_df():
    # SB sempre posta primeiro no log, seguido pelo BB, etc. (ordem na lista de ações pre_flop)
    df = pl.DataFrame({
        "hand_id": ["1", "1", "1", "1", "2", "2"],
        "street": ["PRE_FLOP", "PRE_FLOP", "PRE_FLOP", "PRE_FLOP", "PRE_FLOP", "PRE_FLOP"],
        "player": ["P1", "P2", "P3", "P4", "P1", "P2"] 
    })
    
    res = get_player_positions_df(df)
    
    assert res.height == 6
    # Filtra as posições do hand_id 1 (Mesa de 4)
    pos_h1 = dict(zip(
        res.filter(pl.col("hand_id") == "1")["player"].to_list(), 
        res.filter(pl.col("hand_id") == "1")["position"].to_list()
    ))
    
    assert pos_h1["P1"] == "SB"
    assert pos_h1["P2"] == "BB"
    assert pos_h1["P3"] == "CO"
    assert pos_h1["P4"] == "BTN"
    
    # Filtra as posições do hand_id 2 (Heads-Up, Mesa de 2)
    pos_h2 = dict(zip(
        res.filter(pl.col("hand_id") == "2")["player"].to_list(), 
        res.filter(pl.col("hand_id") == "2")["position"].to_list()
    ))
    
    assert pos_h2["P1"] == "SB"
    assert pos_h2["P2"] == "BB"
