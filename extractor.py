import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Iterator
import json

from src.parser.tokenizer import GGPokerTokenizer, HandStartEvent
from src.fsm.states import InitState, TerminalState, State
from src.domain.models import HandContext
from src.etl.loader import HandLoader

def process_file_stream(filepath: Path, tokenizer, initial_state: State) -> Iterator[HandContext]:
    current_state = initial_state
    hand_context = None
    
    print(f" -> Lendo stream de: {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            token = tokenizer.parse_line(line)
            if not token:
                continue
            
            if isinstance(current_state, HandStartEvent) and hand_context is not None:
                if len(hand_context.actions) > 0:
                    yield hand_context
                
                current_state = initial_state
                hand_context = None

            current_state, hand_context = current_state.process(token, hand_context)

            if isinstance(current_state, TerminalState) and hand_context is not None:
                if len(hand_context.actions) > 0:
                    yield hand_context
                current_state = initial_state
                hand_context = None
                
        if hand_context is not None and len(hand_context.actions) > 0:
            yield hand_context

load_dotenv()
def main():
    
    bronze_dir = Path(os.getenv("DATALAKE_BRONZE"))
    silver_dir = Path(os.getenv("DATALAKE_SILVER"))
    
    bronze_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)
    
    # Controle de extração incremental
    processed_log_path = silver_dir / "processed_files.json"
    processed_files = set()
    if processed_log_path.exists():
        with open(processed_log_path, "r", encoding="utf-8") as f:
            processed_files = set(json.load(f))
            
    all_txt_files = list(bronze_dir.glob("*.txt"))
    new_txt_files = [f for f in all_txt_files if f.name not in processed_files]

    if not all_txt_files:
        print(f"⚠️ Nenhum arquivo .txt encontrado em '{bronze_dir}'.")
        return
        
    if not new_txt_files:
        print("✅ Nenhum arquivo novo para extrair. Datalake atualizado!")
        return

    print(f"🚀 Iniciando Processamento Stream ({len(new_txt_files)} novos arquivos encontrados)...\n")
    
    tokenizer = GGPokerTokenizer()
    initial_state = InitState()
    
    def hand_stream_pipeline() -> Iterator[HandContext]:
        for file_path in new_txt_files:
            yield from process_file_stream(file_path, tokenizer, initial_state)

    print("💾 Iniciando a carga no Polars (ETL - Camada Silver)...\n")
    loader = HandLoader(output_dir=str(silver_dir))
    
    processed_count = loader.process_and_save(hand_stream_pipeline())
    
    if processed_count > 0:
        # Atualiza o log de processados
        processed_files.update([f.name for f in new_txt_files])
        with open(processed_log_path, "w", encoding="utf-8") as f:
            json.dump(list(processed_files), f, indent=4)
        print(f"\n✅ ETL incremental concluído com sucesso!")
    else:
        print("\n⚠️ Nenhum dado extraído dos novos arquivos.")

if __name__ == "__main__":
    main()