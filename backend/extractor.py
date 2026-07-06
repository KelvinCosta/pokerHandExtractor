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
import concurrent.futures
import time

def process_file_worker(file_path: str, platform: str, hero_name: str) -> list:
    # Worker function that runs in a separate process
    from src.parser.tokenizer import TokenizerFactory
    from src.fsm.states import InitState
    from src.etl.loader import HandLoader
    from pathlib import Path
    
    tokenizer = TokenizerFactory.get_tokenizer(platform, hero_name=hero_name)
    initial_state = InitState(platform=platform, hero_name=hero_name)
    loader = HandLoader(output_dir="") # Usado apenas para o transform_hand
    
    file_path_obj = Path(file_path)
    dict_batch = []
    
    try:
        with open(file_path_obj, 'r', encoding='utf-8') as f:
            for hand_context in process_stream(f, file_path_obj.name, tokenizer, initial_state):
                dict_batch.append(loader.transform_hand(hand_context))
    except Exception as e:
        print(f"Erro ao processar arquivo {file_path_obj.name}: {e}")
        
    return dict_batch

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
            hands_files_to_process.append(str(file_path))

    print("💾 Iniciando a carga no Polars (ETL - Camada Silver) com Multiprocessing...\n")
    loader = HandLoader(output_dir=str(silver_dir))
    
    # Salvar Sumários
    if summaries_to_save:
        loader.save_summaries(summaries_to_save)
        
    processed_count = 0
    if hands_files_to_process:
        run_id = int(time.time() * 1000)
        batch_index = 1
        current_batch = []
        batch_size = 10000
        
        # Parallelize the extraction and parsing phase
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [executor.submit(process_file_worker, f, args.platform, args.hero_name) for f in hands_files_to_process]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    hands_dicts = future.result()
                    if hands_dicts:
                        current_batch.extend(hands_dicts)
                        
                    while len(current_batch) >= batch_size:
                        to_save = current_batch[:batch_size]
                        current_batch = current_batch[batch_size:]
                        processed_count += loader.save_dict_batch(to_save, run_id, batch_index)
                        batch_index += 1
                except Exception as e:
                    print(f"Erro em worker process: {e}")
                    
        # Salva o resto do batch
        if current_batch:
            processed_count += loader.save_dict_batch(current_batch, run_id, batch_index)
            
        print(f"📊 Carga completa! Total de mãos particionadas: {processed_count}")
    
    if processed_count > 0 or summaries_to_save:
        # Atualiza o log de processados usando o Repository
        repo.mark_as_processed([f.name for f in new_txt_files])
        print(f"\n✅ ETL incremental concluído com sucesso!")
    else:
        print("\n⚠️ Nenhum dado extraído dos novos arquivos.")

if __name__ == "__main__":
    main()