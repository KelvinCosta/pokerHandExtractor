import json
from pathlib import Path
from typing import Protocol, List, Set

class ProcessedHandsRepository(Protocol):
    def get_processed_sources(self) -> Set[str]:
        """Retorna um conjunto de fontes (arquivos/streams) já processadas."""
        ...

    def mark_as_processed(self, sources: List[str]) -> None:
        """Marca uma lista de fontes como processadas."""
        ...

class JsonProcessedHandsRepository:
    def __init__(self, file_path: Path | str):
        self.file_path = Path(file_path)

    def get_processed_sources(self) -> Set[str]:
        if not self.file_path.exists():
            return set()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()

    def mark_as_processed(self, sources: List[str]) -> None:
        processed = self.get_processed_sources()
        processed.update(sources)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(list(processed), f, indent=4)
