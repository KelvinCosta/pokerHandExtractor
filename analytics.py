import polars as pl
from pathlib import Path

def main():
    # Caminho do nosso banco de dados da Camada Silver
    # Ajuste o caminho se necessário com base no log do seu terminal
    silver_file = Path("D:/ggpoker/Dados/silver/historico_consolidado.parquet")
    
    print("📥 Carregando o Data Lake (Silver Layer)...")
    df_mãos = pl.read_parquet(silver_file)
    print(f"✅ Mãos únicas na memória: {df_mãos.height}\n")
    
    # =========================================================================
    # A MÁGICA: O EXPLODE E O UNNEST
    # Transformando dados aninhados em formato tabular relacional instantaneamente
    # =========================================================================
    print("💥 Criando a visualização analítica (Camada Gold) via DataFrame.explode()...")
    df_actions = (
        df_mãos
        # Se uma mão teve 10 ações na lista, o explode() cria 10 linhas repetindo o ID da mão
        .explode("actions") 
        # O unnest() pega as propriedades internas da Struct (player, action, amount) e vira colunas!
        .unnest("actions")  
    )
    
    print("\n=== PREVIEW DA TABELA EXPLODIDA ===")
    print(df_actions.head(5))
    print(f"Total de ações individuais processadas: {df_actions.height}")

    # =========================================================================
    # QUERY 1: ANÁLISE DE POPULAÇÃO (MDA)
    # Quais são os 5 jogadores mais agressivos do seu field? (Que mais deram Raise)
    # =========================================================================
    print("\n🔥 TOP 5 JOGADORES MAIS AGRESSIVOS (Frequência Bruta de 'RAISES'):")
    top_agressores = (
        df_actions
        .filter(pl.col("action_type") == "RAISES") # Filtra apenas as ações de Raise
        .group_by("player")                        # Agrupa pelo nome do jogador
        .agg(pl.len().alias("total_raises"))       # Conta quantas vezes aconteceu
        .sort("total_raises", descending=True)     # Ordena do maior pro menor
        .head(5)                                   # Pega o Top 5
    )
    print(top_agressores)

    # =========================================================================
    # QUERY 2: ESTATÍSTICA MACRO DA NL2
    # Qual é a distribuição total de ações em toda essa amostra?
    # =========================================================================
    print("\n📊 DISTRIBUIÇÃO GLOBAL DE AÇÕES DA POPULAÇÃO DA NL2:")
    distribuicao_acoes = (
        df_actions
        .group_by("action_type")
        .agg(pl.len().alias("ocorrencias"))
        .sort("ocorrencias", descending=True)
    )
    print(distribuicao_acoes)

if __name__ == "__main__":
    main()