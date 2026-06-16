import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ARQUIVO_TAGS = Path(os.getenv("ARQUIVO_TAGS", "tags_viloes.json"))
DATALAKE_SILVER = Path(os.getenv("DATALAKE_SILVER", "silver"))

def carregar_tags():
    if not os.path.exists(ARQUIVO_TAGS):
        return {}
    with open(ARQUIVO_TAGS, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_tag(jogador, anotacao):
    tags = carregar_tags()
    tags[jogador] = anotacao
    with open(ARQUIVO_TAGS, "w", encoding="utf-8") as f:
        json.dump(tags, f, indent=4, ensure_ascii=False)
