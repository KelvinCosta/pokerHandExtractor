import os
import polars as pl
from typing import Iterator
from itertools import islice
from src.domain.models import HandContext

class HandLoader:
    def __init__(self, output_dir: str):
        
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def process_and_save(self, hands_iterator: Iterator[HandContext], batch_size: int = 10000) -> int:
        total_processed = 0
        batch_index = 1
        
        while True:
            batch = list(islice(hands_iterator, batch_size))
            
            if not batch:
                break
            
            df = pl.DataFrame(batch)
            
            filename = f"hands_part_{batch_index:04d}.parquet"
            file_path = os.path.join(self.output_dir, filename)
            
            df.write_parquet(file_path, compression="zstd")
            print(f"✅ Partição {batch_index:04d} salva: {filename} ({df.height} mãos)")
            
            total_processed += df.height
            batch_index += 1
            
        print(f"📊 Carga completa! Total de mãos particionadas: {total_processed}")
        return total_processed