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
    silver_bucket = os.getenv("S3_SILVER_BUCKET", "poker-silver")
    
    # Garantir que o bucket existe (para ambiente local)
    from src.core.storage import ensure_bucket_exists, upload_file_stream_to_s3, download_file_from_s3, upload_local_file_to_s3
    ensure_bucket_exists(bronze_bucket)
    ensure_bucket_exists(silver_bucket)

    # Usaremos uma pasta temporária para processamento local imediato (o arquivo final ficará no S3)
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    silver_dir = temp_dir / "silver"
    silver_dir.mkdir(parents=True, exist_ok=True)
    
    import uuid
    summary_parser = SummaryParser()
    
    saved_files = []
    used_basenames = set()
    
    # 1. Salvar na camada Bronze (S3) e no temp (Processamento)
    for file in files:
        original_basename = Path(file.filename).name
        
        # Save to a temporary UUID file first
        temp_uuid_name = f"{uuid.uuid4()}.txt"
        temp_uuid_path = temp_dir / temp_uuid_name
        
        with open(temp_uuid_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Determine final basename
        final_basename = original_basename
        if summary_parser.is_summary_file(str(temp_uuid_path)):
            if not final_basename.lower().endswith("_summary.txt"):
                name_part = Path(final_basename).stem
                ext_part = Path(final_basename).suffix
                final_basename = f"{name_part}_summary{ext_part}"
                
        # Handle collisions (if user uploads multiple files with exact same calculated name)
        base_stem = Path(final_basename).stem
        base_ext = Path(final_basename).suffix
        counter = 1
        while final_basename in used_basenames:
            final_basename = f"{base_stem}_{counter}{base_ext}"
            counter += 1
            
        used_basenames.add(final_basename)
        
        # Rename UUID file to final basename
        final_file_path = temp_dir / final_basename
        temp_uuid_path.rename(final_file_path)
        
        # Upload to S3 bronze
        object_name = f"{user_id}/{final_basename}"
        with open(final_file_path, "rb") as f_up:
            upload_file_stream_to_s3(f_up, bronze_bucket, object_name)
            
        saved_files.append(final_file_path)
        
    # 2. Configurar ETL Incremental (Baixando histórico anterior do S3)
    processed_log_path = silver_dir / "processed_files.json"
    download_file_from_s3(silver_bucket, f"{user_id}/processed_files.json", str(processed_log_path))
    
    tournaments_path = silver_dir / "tournaments.parquet"
    download_file_from_s3(silver_bucket, f"{user_id}/tournaments.parquet", str(tournaments_path))

    
    # 2.1 Checar Versão do ETL e resetar Silver se necessário
    ETL_VERSION = "v4.02"
    from src.core.storage import get_s3_client
    s3 = get_s3_client()
    try:
        version_obj = s3.get_object(Bucket=silver_bucket, Key=f"{user_id}/etl_version.txt")
        current_version = version_obj['Body'].read().decode('utf-8')
    except Exception:
        current_version = "unknown"
        
    if current_version != ETL_VERSION:
        print(f"⚠️ Versão ETL mudou de '{current_version}' para '{ETL_VERSION}'. Resetando a Silver Layer do usuário {user_id}...")
        objects = s3.list_objects_v2(Bucket=silver_bucket, Prefix=f"{user_id}/")
        if 'Contents' in objects:
            for obj in objects['Contents']:
                s3.delete_object(Bucket=silver_bucket, Key=obj['Key'])
        # Limpa o tracking local para processar tudo de novo
        if processed_log_path.exists():
            processed_log_path.unlink()
        
        hands_path = silver_dir / "hands.parquet"
        if hands_path.exists():
            hands_path.unlink()
            
        if tournaments_path.exists():
            tournaments_path.unlink()
            
        s3.put_object(Bucket=silver_bucket, Key=f"{user_id}/etl_version.txt", Body=ETL_VERSION.encode('utf-8'))
    
    repo = JsonProcessedHandsRepository(processed_log_path)
    processed_files = repo.get_processed_sources()
    
    new_txt_files = [f for f in saved_files if f.name not in processed_files]
    
    if not new_txt_files:
        shutil.rmtree(temp_dir, ignore_errors=True)
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
        
        # Fazendo Upload da Camada Silver atualizada para o S3
        for silver_file in silver_dir.iterdir():
            if silver_file.is_file():
                upload_local_file_to_s3(str(silver_file), silver_bucket, f"{user_id}/{silver_file.name}")
        
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

@router.get("/processed")
async def get_processed_files(current_user: User = Depends(get_current_user)):
    try:
        from src.core.storage import get_s3_client
        s3 = get_s3_client()
        silver_bucket = os.getenv("S3_SILVER_BUCKET", "poker-silver")
        
        # Check version
        try:
            version_obj = s3.get_object(Bucket=silver_bucket, Key=f"{current_user.id}/etl_version.txt")
            current_version = version_obj['Body'].read().decode('utf-8')
        except:
            current_version = "unknown"
            
        ETL_VERSION = "v4.04"
        if current_version != ETL_VERSION:
            return {"processed": [], "version_mismatch": True}

        obj = s3.get_object(Bucket=silver_bucket, Key=f"{current_user.id}/processed_files.json")
        import json
        data = json.loads(obj["Body"].read().decode("utf-8"))
        return {"processed": data, "version_mismatch": False}
    except Exception as e:
        return {"processed": [], "version_mismatch": False}

@router.post("/reprocess")
async def reprocess_datalake(current_user: User = Depends(get_current_user)):
    """
    Downloads all raw files from the Bronze layer in S3 and rebuilds the Silver layer.
    Used when the ETL schema changes (e.g., adding hole cards).
    """
    from src.core.storage import get_s3_client, download_file_from_s3, upload_local_file_to_s3
    from src.etl.loader import HandLoader
    from src.parser.summary_parser import SummaryParser
    from extractor import process_stream
    from src.parser.tokenizer import TokenizerFactory
    from src.fsm.states import InitState
    import shutil
    
    tokenizer = TokenizerFactory.get_tokenizer("ggpoker")
    initial_state = InitState()
    summary_parser = SummaryParser()
    
    s3 = get_s3_client()
    bronze_bucket = os.getenv("S3_BRONZE_BUCKET", "poker-bronze")
    silver_bucket = os.getenv("S3_SILVER_BUCKET", "poker-silver")
    user_id = str(current_user.id)
    ETL_VERSION = "v4.04"
    
    temp_dir = Path("data/temp") / user_id
    silver_dir = Path("data/silver") / user_id
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)
    
    # Limpa arquivos locais residuais
    for f in silver_dir.iterdir():
        if f.is_file():
            f.unlink()
            
    # Remove Silver no S3
    try:
        objects_to_delete = s3.list_objects_v2(Bucket=silver_bucket, Prefix=f"{user_id}/")
        if 'Contents' in objects_to_delete:
            for obj in objects_to_delete['Contents']:
                s3.delete_object(Bucket=silver_bucket, Key=obj['Key'])
    except Exception as e:
        pass
        
    s3.put_object(Bucket=silver_bucket, Key=f"{user_id}/etl_version.txt", Body=ETL_VERSION.encode('utf-8'))
    
    # Baixar todos os arquivos do Bronze
    print("Baixando arquivos da camada Bronze...")
    new_txt_files = []
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bronze_bucket, Prefix=f"{user_id}/")
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    file_key = obj['Key']
                    if not file_key.endswith(".txt"):
                        continue
                    file_name = file_key.split("/")[-1]
                    local_path = temp_dir / file_name
                    s3.download_file(bronze_bucket, file_key, str(local_path))
                    new_txt_files.append(local_path)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"error": f"Erro ao acessar camada Bronze: {str(e)}"}
        
    if not new_txt_files:
        shutil.rmtree(temp_dir, ignore_errors=True)
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
        
        # Fazendo Upload da Camada Silver atualizada para o S3
        for silver_file in silver_dir.iterdir():
            if silver_file.is_file():
                upload_local_file_to_s3(str(silver_file), silver_bucket, f"{user_id}/{silver_file.name}")
        
        from src.api.dependencies import invalidate_cache
        invalidate_cache(user_id)
        
    shutil.rmtree(temp_dir, ignore_errors=True)
        
    return {
        "message": "ETL Reprocessado com sucesso",
        "new_files": len(new_txt_files),
        "hands_processed": processed_count
    }
