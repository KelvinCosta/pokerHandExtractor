import os
import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from src.database.models import User
from src.api.dependencies import get_current_user

from src.parser.tokenizer import TokenizerFactory
from src.fsm.states import InitState
from src.etl.loader import HandLoader
from src.etl.repository import JsonProcessedHandsRepository
from src.parser.summary_parser import SummaryParser
from extractor import process_stream

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

    user_id = current_user.id
    
    bronze_bucket = os.getenv("S3_BRONZE_BUCKET", "poker-bronze")
    
    # Garantir que o bucket existe (para ambiente local)
    from src.core.storage import ensure_bucket_exists, upload_file_stream_to_s3
    ensure_bucket_exists(bronze_bucket)

    silver_dir = Path(os.getenv("DATALAKE_SILVER", "./datalake/silver")) / user_id
    silver_dir.mkdir(parents=True, exist_ok=True)
    
    # Usaremos uma pasta temporária para processamento local imediato (o arquivo final ficará no S3)
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    
    saved_files = []
    
    # 1. Salvar na camada Bronze (S3) e no temp (Processamento)
    for file in files:
        # Quando o usuário sobe um diretório (webkitdirectory), o filename contém a rota relativa (ex: pasta/arquivo.txt)
        # Precisamos apenas do nome final do arquivo para não quebrar a criação local no temp
        basename = Path(file.filename).name
        
        # Primeiro, envia o arquivo para o S3 (Cloud/MinIO)
        object_name = f"{user_id}/{basename}"
        
        # Como o FastAPI recebe em stream, vamos salvar no temp primeiro e depois subir
        temp_file_path = temp_dir / basename
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        with open(temp_file_path, "rb") as f_up:
            upload_file_stream_to_s3(f_up, bronze_bucket, object_name)
            
        saved_files.append(temp_file_path)
        
    # 2. Configurar ETL Incremental
    processed_log_path = silver_dir / "processed_files.json"
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

    # Função geradora
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
        from src.api.dependencies import invalidate_cache
        invalidate_cache(user_id)
        
    # 3. Limpeza do disco local (Tudo já está no S3 / Parquets no Silver)
    shutil.rmtree(temp_dir, ignore_errors=True)
        
    return {
        "message": "ETL concluído com sucesso",
        "new_files": len(new_txt_files),
        "hands_processed": processed_count
    }
