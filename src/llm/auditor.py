import json
import argparse
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate

# Importando nossos módulos locais
from src.db.warehouse import DuckDBWarehouse
from src.llm.state_builder import SessionStateCalculator
from src.dashboard.config import DATALAKE_SILVER

def auditar_estado_cognitivo_local(payload_json, modelo="llama3"):
    """
    Função que usa LangChain e Ollama para auditar o JSON localmente.
    """
    
    # 1. Instanciar o modelo local
    try:
        llm = Ollama(model=modelo) 
    except Exception as e:
        print(f"Erro ao conectar com Ollama: {e}")
        print("Certifique-se de que o Ollama está rodando (ollama run llama3)")
        return None

    # 2. Criar o Template Socrático
    template = """
    Você é um mentor de alta performance focado na psicologia de jogadores profissionais de Poker.
    
    Regras estritas:
    1. Nunca dê sermões, dicas técnicas ou explique a matemática.
    2. Faça APENAS UMA pergunta socrática, curta e direta, focada no estado mental do jogador.
    3. Avalie apenas os dados abaixo. Foco em anomalias como quedas de agressividade (agressiveness_deviation negativo) ou fadiga (session_duration_minutes).
    
    Dados da Janela Atual da Sessão:
    {dados_do_jogador}
    
    Escreva abaixo ÚNICA e EXCLUSIVAMENTE a sua pergunta socrática:
    """
    
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm

    # 3. Injetar o JSON e executar
    dados_str = json.dumps(payload_json, indent=2)
    print(f"🧠 Processando análise via Ollama (modelo: {modelo})... Aguarde.")
    
    try:
        resposta = chain.invoke({"dados_do_jogador": dados_str})
        return resposta
    except Exception as e:
        print(f"Falha na comunicação com o modelo local: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Auditoria Socrática da Sessão de Poker")
    parser.add_argument("--hero", type=str, default="Hero", help="Nome do herói nas mãos")
    parser.add_argument("--hands", type=int, default=20, help="Número de mãos para a janela (Sliding Window)")
    parser.add_argument("--model", type=str, default="llama3", help="Modelo local no Ollama (ex: llama3, phi3, gemma2)")
    args = parser.parse_args()

    print(f"📊 Extraindo as últimas {args.hands} mãos do Datalake Silver para '{args.hero}'...")
    
    # Busca dados reais do banco usando a arquitetura já estabelecida
    warehouse = DuckDBWarehouse(silver_dir=str(DATALAKE_SILVER))
    calculator = SessionStateCalculator(warehouse)
    
    estado_json = calculator.get_current_state(hero_name=args.hero, num_hands=args.hands)
    
    estado_json["context_window_info"] = {
        "num_hands_analyzed": args.hands,
        "hero_name": args.hero
    }
    
    print("\n--- DADOS ENVIADOS PARA A IA ---")
    print(json.dumps(estado_json, indent=2))
    print("--------------------------------\n")
    
    # Chama o motor da LangChain
    alerta_na_tela = auditar_estado_cognitivo_local(estado_json, modelo=args.model)
    
    if alerta_na_tela:
        print("\n=== 🔮 FEEDBACK DO MENTOR ===")
        print(alerta_na_tela.strip())
        print("===============================\n")

if __name__ == "__main__":
    main()
