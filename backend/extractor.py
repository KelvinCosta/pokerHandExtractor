import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Iterator, Iterable
import json
from dataclasses import replace

from src.parser.tokenizer import TokenizerFactory, HandStartEvent
from src.fsm.states import InitState, TerminalState, State
from src.domain.models import HandContext
from src.etl.loader import HandLoader
from src.etl.repository import JsonProcessedHandsRepository
from src.parser.summary_parser import SummaryParser
import argparse

def process_stream(stream: Iterable[str], source_name: str, tokenizer, initial_state: State) -> Iterator[HandContext]:
    current_state = initial_state
    hand_context = None
    
    print(f" -> Processando stream: {source_name}...")
    
    for line in stream:
        token = tokenizer.parse_line(line)
        if not token:
            continue
        
        if isinstance(token, HandStartEvent) and hand_context is not None:
            if len(hand_context.actions) > 0:
                yield replace(hand_context, source_file=source_name)
            
            current_state = initial_state
            hand_context = None

        current_state, hand_context = current_state.process(token, hand_context)
            
    if hand_context is not None and len(hand_context.actions) > 0:
        yield replace(hand_context, source_file=source_name)

load_dotenv()
def main():
    parser = argparse.ArgumentParser(description="Processador ETL de Históricos de Mãos de Poker")
    parser.add_argument("--platform", required=True, help="Plataforma de origem (ex: ggpoker)")
    parser.add_argument("--hero_name", required=True, help="Nickname real do jogador dono do histórico")
    parser.add_argument("--user_id", required=True, help="ID do Usuário para salvar no Datalake Multilocatário")
    args = parser.parse_args()
    
    bronze_dir = Path(os.getenv("DATALAKE_BRONZE"))
    silver_dir = Path(os.getenv("DATALAKE_SILVER")) / args.user_id
    
    bronze_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)
    
    # Controle de extração incremental usando Repository
    processed_log_path = silver_dir / "processed_files.json"
    repo = JsonProcessedHandsRepository(processed_log_path)
    processed_files = repo.get_processed_sources()
            
    all_txt_files = list(bronze_dir.glob("*.txt"))
    new_txt_files = [f for f in all_txt_files if f.name not in processed_files]

    if not all_txt_files:
        print(f"⚠️ Nenhum arquivo .txt encontrado em '{bronze_dir}'.")
        return
        
    if not new_txt_files:
        print("✅ Nenhum arquivo novo para extrair. Datalake atualizado!")
        return

    print(f"🚀 Iniciando Processamento Stream ({len(new_txt_files)} novos arquivos encontrados)...\n")
    print(f"👤 Jogador logado: {args.hero_name} | 🌐 Plataforma: {args.platform}")
    
    tokenizer = TokenizerFactory.get_tokenizer(args.platform, hero_name=args.hero_name)
    initial_state = InitState(platform=args.platform, hero_name=args.hero_name)
    summary_parser = SummaryParser()
    
    summaries_to_save = []
    hands_files_to_process = []
    
    # 1. Separar Sumários vs Históricos de Mãos
    for file_path in new_txt_files:
        if summary_parser.is_summary_file(str(file_path)):
            summary = summary_parser.parse_file(str(file_path))
            if summary:
                summaries_to_save.append(summary)
        else:
            hands_files_to_process.append(file_path)

    def hand_stream_pipeline() -> Iterator[HandContext]:
        for file_path in hands_files_to_process:
            with open(file_path, 'r', encoding='utf-8') as f:
                yield from process_stream(f, file_path.name, tokenizer, initial_state)

    print("💾 Iniciando a carga no Polars (ETL - Camada Silver)...\n")
    loader = HandLoader(output_dir=str(silver_dir))
    
    # Salvar Sumários
    if summaries_to_save:
        loader.save_summaries(summaries_to_save)
        
    processed_count = 0
    if hands_files_to_process:
        processed_count = loader.process_and_save(hand_stream_pipeline())
    
    if processed_count > 0 or summaries_to_save:
        # Atualiza o log de processados usando o Repository
        repo.mark_as_processed([f.name for f in new_txt_files])
        print(f"\n✅ ETL incremental concluído com sucesso!")
    else:
        print("\n⚠️ Nenhum dado extraído dos novos arquivos.")

if __name__ == "__main__":
    main()