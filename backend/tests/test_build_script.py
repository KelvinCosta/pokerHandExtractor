import pytest
import os
from pathlib import Path

def test_stream_to_logger_has_bugfixes():
    """
    Testa se o script gerador do boot.py possui as correções vitais para:
    1. isatty() - Para evitar que o Uvicorn crash ao checar suporte a cores no terminal.
    2. UnicodeEncodeError - Para evitar crash quando for imprimir emojis (ex: ✅) no terminal Windows CP1252.
    """
    root_dir = Path(__file__).resolve().parent.parent.parent
    build_script = root_dir / "build.py"
    
    assert build_script.exists(), "O script build.py não foi encontrado na raiz do projeto"
    
    with open(build_script, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Verifica o suporte ao UnicodeEncodeError (Emoji Fix)
    assert "except UnicodeEncodeError:" in content, "O fix de UnicodeEncodeError para Emojis não foi encontrado no StreamToLogger"
    assert "errors='replace'" in content, "O fallback encoding ASCII não foi encontrado"
    
    # Verifica o suporte ao isatty (Uvicorn color fix)
    assert "def isatty(self):" in content, "A função isatty() não foi encontrada no StreamToLogger"
    assert "return False" in content, "A função isatty() deve retornar False para evitar crashes do Uvicorn"
    
    # Verifica fallback de métodos dinâmicos
    assert "def __getattr__(self, name):" in content, "O método __getattr__ não foi implementado no StreamToLogger"
