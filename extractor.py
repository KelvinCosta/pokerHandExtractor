from src.parser.tokenizer import GGPokerTokenizer
from src.fsm.states import InitState
from src.etl.loader import HandLoader
from pathlib import Path

def process_file(filepath: Path) -> list:
    """Processa um único arquivo de texto e retorna a lista de mãos parseadas."""
    tokenizer = GGPokerTokenizer()
    current_state = InitState()
    hand_context = None
    finished_hands = []
    
    print(f" -> Lendo o arquivo: {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            token = tokenizer.parse_line(line)
            if token:
                # Se for o início de uma NOVA mão e já tínhamos um contexto aberto,
                # significa que a mão anterior acabou de fato. Salvamos e resetamos.
                if token.__class__.__name__ == "HandStartEvent" and hand_context is not None:
                    finished_hands.append(hand_context)
                    current_state = InitState()
                    hand_context = None

                # Empurra o token para a Máquina de Estados
                current_state, hand_context = current_state.process(token, hand_context)

        # Fim do arquivo (EOF - End Of File). 
        # Não podemos esquecer de salvar a última mão que ficou retida na memória!
        if hand_context is not None:
            finished_hands.append(hand_context)
            
    return finished_hands

def main():
    # 1. Define os caminhos das camadas do nosso Data Lake local
    bronze_dir = Path("D:/ggpoker/Dados/bronze")
    silver_dir = Path("D:/ggpoker/Dados/silver")
    
    # Garante que a pasta bronze exista (para não quebrar se for a primeira vez)
    bronze_dir.mkdir(parents=True, exist_ok=True)

    # 2. Busca todos os arquivos .txt dentro da camada bronze
    txt_files = list(bronze_dir.glob("*.txt"))

    if not txt_files:
        print(f"⚠️ Nenhum arquivo .txt encontrado em '{bronze_dir}'.")
        print("Cole seus históricos de mãos lá e rode o script novamente.")
        return

    print(f"🚀 Iniciando Processamento Batch ({len(txt_files)} arquivos encontrados na Bronze)...\n")
    
    all_finished_hands = []

    # 3. Itera sobre cada arquivo encontrado e acumula os resultados
    for file_path in txt_files:
        hands_from_file = process_file(file_path)
        all_finished_hands.extend(hands_from_file)

    print(f"\n✅ Extração concluída! Total geral de mãos em memória: {len(all_finished_hands)}")
    print("💾 Iniciando a carga no Polars (ETL - Camada Silver)...\n")
    
    # 4. Envia tudo para o Loader salvar em um único Parquet massivo
    # Note que passamos o silver_dir convertendo pra string, pois o os.path no Loader espera string
    loader = HandLoader(output_dir=str(silver_dir))
    df = loader.process_and_save(all_finished_hands, filename="historico_consolidado.parquet")

if __name__ == "__main__":
    main()