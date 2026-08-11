import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
import json
from src.database.models import User
from src.api.dependencies import get_current_user

from src.parser.tokenizer import TokenizerFactory
from src.fsm.states import InitState
from src.etl.loader import HandLoader
from src.etl.repository import JsonProcessedHandsRepository
from src.parser.summary_parser import SummaryParser
from extractor import process_stream
from src.api.dependencies import invalidate_cache

CURRENT_ETL_VERSION = "v5.00"

router = APIRouter(prefix="/api/etl", tags=["ETL Upload"])

@router.post("/upload")
async def upload_and_process(
    platform: str = Form(...),
    hero_name: str = Form(...),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

    user_id = str(current_user.id)
    
    bronze_dir = Path(os.getenv("DATALAKE_BRONZE", "data/bronze")) / user_id
    silver_dir = Path(os.getenv("DATALAKE_SILVER", "data/silver")) / user_id
    
    bronze_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)
    
    summary_parser = SummaryParser()
    
    saved_files = []
    used_basenames = set()
    
    # 1. Salvar na camada Bronze local
    for file in files:
        original_basename = Path(file.filename).name
        
        # Save to a temporary UUID file first to prevent mid-upload collisions
        temp_uuid_name = f"{uuid.uuid4()}.txt"
        temp_uuid_path = bronze_dir / temp_uuid_name
        
        with open(temp_uuid_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Determine final basename
        final_basename = original_basename
        if summary_parser.is_summary_file(str(temp_uuid_path)):
            if not final_basename.lower().endswith("_summary.txt"):
                name_part = Path(final_basename).stem
                ext_part = Path(final_basename).suffix
                final_basename = f"{name_part}_summary{ext_part}"
                
        # Handle collisions
        base_stem = Path(final_basename).stem
        base_ext = Path(final_basename).suffix
        counter = 1
        while final_basename in used_basenames:
            final_basename = f"{base_stem}_{counter}{base_ext}"
            counter += 1
            
        used_basenames.add(final_basename)
        
        # Rename UUID file to final basename
        final_file_path = bronze_dir / final_basename
        
        try:
            # Em sistemas Windows, se o arquivo estiver bloqueado por outro processo (ex: GC ainda não fechou, ou antivírus)
            if final_file_path.exists():
                final_file_path.unlink()
            temp_uuid_path.rename(final_file_path)
            saved_files.append(final_file_path)
        except PermissionError:
            # Se falhar por bloqueio de permissão, geramos um novo nome com sufixo
            import time
            final_basename = f"{base_stem}_{int(time.time()*1000)}{base_ext}"
            final_file_path = bronze_dir / final_basename
            temp_uuid_path.rename(final_file_path)
            saved_files.append(final_file_path)
        
    # 2. Configurar ETL Incremental
    processed_log_path = silver_dir / "processed_files.json"
    tournaments_path = silver_dir / "tournaments.parquet"

    # 2.1 Checar Versão do ETL e resetar Silver se necessário
    ETL_VERSION = CURRENT_ETL_VERSION
    try:
        current_version = (silver_dir / "etl_version.txt").read_text(encoding='utf-8')
    except Exception:
        current_version = "unknown"
        
    if current_version != ETL_VERSION:
        print(f"⚠️ Versão ETL mudou de '{current_version}' para '{ETL_VERSION}'. Resetando a Silver Layer do usuário {user_id}...")
        for f in silver_dir.iterdir():
            if f.is_file():
                f.unlink()
        (silver_dir / "etl_version.txt").write_text(ETL_VERSION, encoding='utf-8')
    
    repo = JsonProcessedHandsRepository(processed_log_path)
    processed_files = repo.get_processed_sources()
    
    new_txt_files = [f for f in saved_files if f.name not in processed_files]
    
    if not new_txt_files:
        return {"message": "Arquivos já foram processados anteriormente", "processed": 0}
        
    tokenizer = TokenizerFactory.get_tokenizer(platform, hero_name=hero_name)
    initial_state = InitState(platform=platform, hero_name=hero_name)
    summary_parser = SummaryParser()
    
    summaries_to_save = []
    hands_files_to_process = []
    
    for file_path in new_txt_files:
        if summary_parser.is_summary_file(str(file_path)):
            summary = summary_parser.parse_file(str(file_path))
            if summary:
                summaries_to_save.append(summary)
        else:
            hands_files_to_process.append(file_path)

    def hand_stream_pipeline():
        for file_path in hands_files_to_process:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                yield from process_stream(f, file_path.name, tokenizer, initial_state)

    loader = HandLoader(output_dir=str(silver_dir))
    
    if summaries_to_save:
        loader.save_summaries(summaries_to_save)
        
    processed_count = 0
    if hands_files_to_process:
        processed_count = loader.process_and_save(hand_stream_pipeline())
    
    if processed_count > 0 or summaries_to_save:
        repo.mark_as_processed([f.name for f in new_txt_files])
        # Invalida o cache em memória do usuário para forçar recarga no próximo request do Dashboard
        invalidate_cache(user_id)
        
    return {
        "message": "ETL concluído com sucesso",
        "new_files": len(new_txt_files),
        "hands_processed": processed_count
    }

@router.get("/processed")
async def get_processed_files(current_user: User = Depends(get_current_user)):
    try:
        silver_dir = Path(os.getenv("DATALAKE_SILVER", "data/silver")) / str(current_user.id)
        
        # Check version
        try:
            current_version = (silver_dir / "etl_version.txt").read_text(encoding='utf-8')
        except Exception:
            current_version = "unknown"
            
        ETL_VERSION = CURRENT_ETL_VERSION
        if current_version != ETL_VERSION:
            return {"processed": [], "version_mismatch": True}

        processed_path = silver_dir / "processed_files.json"
        if processed_path.exists():
            data = json.loads(processed_path.read_text(encoding="utf-8"))
            return {"processed": data, "version_mismatch": False}
            
        return {"processed": [], "version_mismatch": False}
    except Exception as e:
        return {"processed": [], "version_mismatch": False}

@router.post("/reprocess")
async def reprocess_datalake(current_user: User = Depends(get_current_user)):
    """
    Reads all raw files from the local Bronze layer and rebuilds the Silver layer.
    Used when the ETL schema changes (e.g., adding hole cards).
    """
    from src.etl.loader import HandLoader
    from src.parser.summary_parser import SummaryParser
    from extractor import process_stream
    from src.parser.tokenizer import TokenizerFactory
    from src.fsm.states import InitState
    
    tokenizer = TokenizerFactory.get_tokenizer("ggpoker")
    initial_state = InitState()
    summary_parser = SummaryParser()
    
    user_id = str(current_user.id)
    ETL_VERSION = CURRENT_ETL_VERSION
    
    bronze_dir = Path(os.getenv("DATALAKE_BRONZE", "data/bronze")) / user_id
    silver_dir = Path(os.getenv("DATALAKE_SILVER", "data/silver")) / user_id
    
    bronze_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)
    
    # Limpa arquivos locais na Silver (reset)
    for f in silver_dir.iterdir():
        if f.is_file():
            f.unlink()
            
    (silver_dir / "etl_version.txt").write_text(ETL_VERSION, encoding='utf-8')
    
    # Pegar todos os arquivos do Bronze
    print("Buscando arquivos locais na camada Bronze...")
    new_txt_files = list(bronze_dir.glob("*.txt"))
        
    if not new_txt_files:
        return {"message": "Nenhum arquivo encontrado na camada Bronze.", "new_files": 0, "hands_processed": 0}
        
    from src.etl.repository import JsonProcessedHandsRepository
    repo = JsonProcessedHandsRepository(silver_dir / "processed_files.json")
    
    summaries_to_save = []
    hands_files_to_process = []
    
    for file_path in new_txt_files:
        if summary_parser.is_summary_file(str(file_path)):
            summary = summary_parser.parse_file(str(file_path))
            if summary:
                summaries_to_save.append(summary)
        else:
            hands_files_to_process.append(file_path)

    def hand_stream_pipeline():
        for file_path in hands_files_to_process:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                yield from process_stream(f, file_path.name, tokenizer, initial_state)

    loader = HandLoader(output_dir=str(silver_dir))
    
    if summaries_to_save:
        loader.save_summaries(summaries_to_save)
        
    processed_count = 0
    if hands_files_to_process:
        processed_count = loader.process_and_save(hand_stream_pipeline())
    
    if processed_count > 0 or summaries_to_save:
        repo.mark_as_processed([f.name for f in new_txt_files])
        invalidate_cache(user_id)
        
    return {
        "message": "ETL Reprocessado com sucesso",
        "new_files": len(new_txt_files),
        "hands_processed": processed_count
    }
