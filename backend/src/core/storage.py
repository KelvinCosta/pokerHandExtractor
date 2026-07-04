import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional

def get_s3_client():
    """
    Retorna uma instância do client S3 (boto3) conectado 
    ao Endpoint configurado no .env (MinIO, R2, AWS).
    """
    return boto3.client(
        's3',
        endpoint_url=os.getenv('S3_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('S3_SECRET_KEY'),
        # Necessário para MinIO e R2:
        region_name='us-east-1' 
    )

def ensure_bucket_exists(bucket_name: str):
    """
    Cria o bucket se ele não existir (útil para desenvolvimento local com MinIO).
    """
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            s3.create_bucket(Bucket=bucket_name)
        else:
            raise

def upload_file_stream_to_s3(file_obj, bucket: str, object_name: str) -> bool:
    """
    Faz upload de um file-like object diretamente para o S3.
    """
    s3 = get_s3_client()
    try:
        s3.upload_fileobj(file_obj, bucket, object_name)
        return True
    except ClientError as e:
        print(f"Erro ao fazer upload para o S3: {e}")
        return False

def download_file_from_s3(bucket: str, object_name: str, file_path: str) -> bool:
    """
    Faz o download do arquivo do S3 para o disco local temporário.
    """
    s3 = get_s3_client()
    try:
        s3.download_file(bucket, object_name, file_path)
        return True
    except ClientError as e:
        print(f"Erro ao fazer download do S3: {e}")
        return False
