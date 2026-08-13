import os
import shutil
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch, MagicMock

# Ajusta o import de src
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.main import app
from src.api.dependencies import get_current_user
from src.database.models import User
from src.api.routers.etl import migrate_bronze_layer

client = TestClient(app)

# Mock de um usuário para os testes
mock_user = User(id="test_user_etl", email="test_etl@test.com")

def override_get_current_user():
    return mock_user

app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.fixture
def setup_datalake():
    """Cria um datalake temporário simulando a estrutura antiga e nova."""
    temp_dir = tempfile.mkdtemp()
    
    bronze_dir = Path(temp_dir) / "bronze" / mock_user.id
    silver_dir = Path(temp_dir) / "silver" / mock_user.id
    
    bronze_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)
    
    # Prepara environment variables para apontar para o tmp
    os.environ["DATALAKE_BRONZE"] = str(Path(temp_dir) / "bronze")
    os.environ["DATALAKE_SILVER"] = str(Path(temp_dir) / "silver")
    
    yield bronze_dir, silver_dir
    
    # Limpa
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_migrate_bronze_layer(setup_datalake):
    bronze_dir, _ = setup_datalake
    
    # 1. Simular arquivos antigos (na raiz do bronze)
    (bronze_dir / "legacy_hand_1.txt").write_text("hand content", encoding="utf-8")
    (bronze_dir / "legacy_hand_2.txt").write_text("hand content", encoding="utf-8")
    
    # 2. Executar a migração isolada
    migrate_bronze_layer(bronze_dir)
    
    # 3. Validar se os arquivos foram movidos
    assert not (bronze_dir / "legacy_hand_1.txt").exists()
    assert not (bronze_dir / "legacy_hand_2.txt").exists()
    
    # Espera-se que estejam em ggpoker/Hero
    assert (bronze_dir / "ggpoker" / "Hero" / "legacy_hand_1.txt").exists()
    assert (bronze_dir / "ggpoker" / "Hero" / "legacy_hand_2.txt").exists()

@patch("src.etl.loader.HandLoader.process_and_save")
@patch("src.api.routers.etl.process_stream")
@patch("src.parser.tokenizer.TokenizerFactory.get_tokenizer")
def test_reprocess_datalake_dynamic_grouping(mock_get_tokenizer, mock_process_stream, mock_process_and_save, setup_datalake):
    bronze_dir, _ = setup_datalake
    
    # Prepara o Mock do Loader para não quebrar
    mock_process_and_save.return_value = 5 # simulando 5 mãos processadas
    
    # Simula 3 arquivos em pastas diferentes (2 plataformas)
    gg_hero1_dir = bronze_dir / "ggpoker" / "Lorkel"
    gg_hero1_dir.mkdir(parents=True)
    (gg_hero1_dir / "hand_gg.txt").write_text("gg content", encoding="utf-8")
    
    ps_hero2_dir = bronze_dir / "pokerstars" / "OtherLorkel"
    ps_hero2_dir.mkdir(parents=True)
    (ps_hero2_dir / "hand_ps.txt").write_text("ps content", encoding="utf-8")
    
    legacy_file = bronze_dir / "legacy.txt"
    legacy_file.write_text("legacy content", encoding="utf-8")
    
    # Executa o reprocessamento
    response = client.post("/api/etl/reprocess")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "ETL Reprocessado com sucesso"
    assert data["new_files"] == 3
    # 5 mãos por chamada do process_and_save.
    # Temos 3 arquivos em 3 configs (ggpoker/Lorkel, pokerstars/OtherLorkel, ggpoker/Hero -> migrado)
    # mock foi chamado 3 vezes (uma para cada platform/hero combo), então 3 * 5 = 15
    
    assert data["hands_processed"] == 15
    
    # Verifica se os tokenizers corretos foram solicitados!
    # Tem que ter chamado ggpoker/Hero (migrado), ggpoker/Lorkel, e pokerstars/OtherLorkel
    calls = [call_args[0] for call_args, _ in mock_get_tokenizer.call_args_list]
    kwargs = [call_args[1] for call_args in mock_get_tokenizer.call_args_list]
    
    # Validando chamadas ao TokenizerFactory para garantir extração dinâmica
    assert ("ggpoker",) in calls
    assert ("pokerstars",) in calls
    
    hero_names_passed = [kw.get('hero_name') for kw in kwargs]
    assert "Hero" in hero_names_passed
    assert "Lorkel" in hero_names_passed
    assert "OtherLorkel" in hero_names_passed
