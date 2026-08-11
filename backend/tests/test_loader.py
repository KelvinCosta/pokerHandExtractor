import pytest
import sys
import os
import polars as pl

# Adiciona a raiz do projeto ao path do Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.etl.loader import HandLoader
from src.domain.models import HandContext, Action, ActionType, Street

def test_hand_loader_initialization(tmp_path):
    """Testa se o HandLoader cria o diretório de destino se ele não existir."""
    output_dir = tmp_path / "silver"
    HandLoader(output_dir=str(output_dir))
    
    assert os.path.exists(output_dir)

def test_process_and_save_empty_iterator(tmp_path):
    """Testa o comportamento do Loader quando o iterador está vazio."""
    output_dir = tmp_path / "silver"
    loader = HandLoader(output_dir=str(output_dir))
    
    processed = loader.process_and_save(iter([]))
    
    assert processed == 0
    assert len(os.listdir(output_dir)) == 0

def test_process_and_save_batching(tmp_path):
    """Testa se o particionamento (batch_size) está dividindo os arquivos corretamente."""
    output_dir = tmp_path / "silver"
    loader = HandLoader(output_dir=str(output_dir))
    
    def mock_iterator():
        for i in range(5):
            yield HandContext(
                hand_id=str(i),
                timestamp="2026",
                source_file="file.txt"
            )
            
    # Configura batch_size = 2 para forçar a criação de múltiplos arquivos parquet
    processed = loader.process_and_save(mock_iterator(), batch_size=2)
    
    assert processed == 5
    files = sorted(os.listdir(output_dir))
    assert len(files) == 3
    assert files[0].endswith("_1.parquet")
    assert files[1].endswith("_2.parquet")
    assert files[2].endswith("_3.parquet")

def test_process_and_save_dataframe_schema_and_features(tmp_path):
    """Testa a lógica de transformação do DataFrame, como texturas de Flop e detecção de vitória."""
    output_dir = tmp_path / "silver"
    loader = HandLoader(output_dir=str(output_dir))
    
    # Mão 1: Rainbow, Unpaired
    h1 = HandContext(
        hand_id="1", timestamp="t1", source_file="file.txt",
        board_cards=("Ah", "Kd", "Qs")
    )
    
    # Mão 2: Monotone, Unpaired
    h2 = HandContext(
        hand_id="2", timestamp="t1", source_file="file.txt",
        board_cards=("Th", "Jh", "Qh", "Kh") # (Th, Jh, Qh é o flop)
    )
    
    # Mão 3: Rainbow, Trips
    h3 = HandContext(
        hand_id="3", timestamp="t1", source_file="file.txt",
        board_cards=("8c", "8d", "8h")
    )
    
    # Mão 4: Two-Tone, Paired
    h4 = HandContext(
        hand_id="4", timestamp="t1", source_file="file.txt",
        board_cards=("7s", "7c", "2s")
    )
    
    # Mão 5: Com uma ação de Collect do Hero (vencedor)
    a1 = Action(player="Hero", action_type=ActionType.COLLECT, street=Street.RIVER, amount=50.0)
    h5 = HandContext(
        hand_id="5", timestamp="t1", source_file="file.txt",
        actions=(a1,)
    )

    iterator = iter([h1, h2, h3, h4, h5])
    
    processed = loader.process_and_save(iterator)
    assert processed == 5
    
    # Carrega o parquet gerado para validar as features transformadas pelo Polars
    files = [f for f in os.listdir(output_dir) if f.endswith("_1.parquet")]
    df = pl.read_parquet(str(output_dir / files[0]))
    
    assert df.height == 5
    
    # Validações de textura de Board (Flop Suits)
    row_1 = df.filter(pl.col("hand_id") == "1")
    assert row_1["flop_suit_type"][0] == "Rainbow"
    assert row_1["flop_pair_type"][0] == "Unpaired"
    
    row_2 = df.filter(pl.col("hand_id") == "2")
    assert row_2["flop_suit_type"][0] == "Monotone"
    assert row_2["flop_pair_type"][0] == "Unpaired"
    
    row_3 = df.filter(pl.col("hand_id") == "3")
    assert row_3["flop_suit_type"][0] == "Rainbow"
    assert row_3["flop_pair_type"][0] == "Trips"
    
    row_4 = df.filter(pl.col("hand_id") == "4")
    assert row_4["flop_suit_type"][0] == "Two-Tone"
    assert row_4["flop_pair_type"][0] == "Paired"
    
    # Validação de vitória
    row_5 = df.filter(pl.col("hand_id") == "5")
    assert row_5["hero_ganhou"][0] == True
    assert "Hero" in row_5["lista_vencedores"].to_list()[0]

def test_resume_batch_indexing(tmp_path):
    """Testa se o indexador incremental dos arquivos parquet funciona (hands_part_0005.parquet -> 0006)"""
    output_dir = tmp_path / "silver"
    os.makedirs(output_dir, exist_ok=True)
    
    # Criar um mock de arquivo pré-existente
    with open(output_dir / "hands_part_0005.parquet", "w") as f:
        f.write("dummy")
        
    loader = HandLoader(output_dir=str(output_dir))
    
    def mock_iterator():
        yield HandContext(hand_id="1", timestamp="t", source_file="file")
        
    loader.process_and_save(mock_iterator())
    
    files = sorted(os.listdir(output_dir))
    assert any(f.endswith("_1.parquet") and f != "hands_part_0005.parquet" for f in files)
