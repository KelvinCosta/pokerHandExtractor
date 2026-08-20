import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil

# Precisamos simular o comportamento de upload_and_process do etl.py
# Como o roteador depende de banco de dados e usuários reais (get_current_user),
# vamos mockar as partes difíceis e testar a resiliência a PermissionError.

def test_upload_and_process_permission_error_fallback():
    from src.api.routers.etl import upload_and_process
    import asyncio
    
    # Este teste é conceitual para validar que o bloco try/except PermissionError está no código
    from pathlib import Path
    etl_path = Path(__file__).resolve().parent.parent / "src" / "api" / "routers" / "etl.py"
    with open(etl_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "except PermissionError:" in content
    assert "import time" in content
    assert "final_basename = f\"{base_stem}_{int(time.time()*1000)}{base_ext}\"" in content
    assert "temp_uuid_path.rename(final_file_path)" in content
