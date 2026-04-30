import polars as pl
from typing import List
import os
from src.domain.models import HandContext

class HandLoader:
    """
    Responsável por converter os objetos de domínio em DataFrames aninhados
    e persisti-los no disco (Camada Silver).
    """
    def __init__(self, output_dir: str = "data/silver"):
        self.output_dir = output_dir
        # Garante que a pasta de destino exista
        os.makedirs(self.output_dir, exist_ok=True)

    def process_and_save(self, hands: List[HandContext], filename: str = "hands.parquet") -> pl.DataFrame:
        """
        Converte a lista de contextos em um DataFrame Polars e salva em Parquet.
        """
        # O Polars é inteligente o suficiente para ler listas de dataclasses nativas!
        # Ele automaticamente inferirá que 'actions' é uma Lista de Structs.
        df = pl.DataFrame(hands)
        
        # Salva o arquivo no disco com compressão máxima (zstd)
        file_path = os.path.join(self.output_dir, filename)
        df.write_parquet(file_path, compression="zstd")
        
        print(f"✅ Arquivo Parquet salvo com sucesso em: {file_path}")
        print(f"📊 Total de mãos processadas: {df.height}")
        
        return df