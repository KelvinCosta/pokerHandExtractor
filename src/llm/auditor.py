import json
import argparse
import sys
import os
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import PromptTemplate

# Adiciona a raiz do projeto ao PYTHONPATH para resolver "No module named 'src'"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Importando nossos módulos locais
from src.db.warehouse import DuckDBWarehouse
from src.llm.state_builder import SessionStateCalculator
from src.dashboard.config import DATALAKE_SILVER

def iniciar_mentoria(estado_json, modelo="llama3"):
    """
    Inicia uma sessão interativa de mentoria com a IA, mantendo o contexto da conversa.
    """
    try:
        llm = OllamaLLM(model=modelo) 
    except Exception as e:
        print(f"Erro ao conectar com Ollama: {e}")
        return

    template_inicial = """
    Você é um Agente de Inteligência Artificial especializado em Gestão de Risco para jogadores de Poker. A sua personalidade é fria, analítica, cirúrgica e baseada puramente em dados. Você soa como um "Tech Lead" de engenharia, não como um terapeuta.

Regras de Comportamento:
1. PROIBIDO usar frases de empatia ou atendimento (ex: "Entendi", "Compreendo sua preocupação", "É natural sentir isso"). Vá direto ao ponto.
2. O seu comportamento padrão é a Maiêutica Socrática: faça APENAS UMA pergunta curta e direta baseada nos dados fornecidos (ex: quedas de agressividade ou perdas). Não dê as respostas.
3. Responda única e obrigatoriamente em Português do Brasil (PT-BR).

    Rotina de Exceção (Interrupt Handler):
    SE o jogador fizer uma pergunta direta, pedir esclarecimentos de um termo ou pedir expressamente uma sugestão/dica, MUDE O SEU ESTADO.
    Neste caso:
    A) Responda à dúvida ou dê a sugestão técnica de forma extremamente pragmática (máximo de 2 frases).
    B) Em seguida, encerre com uma nova pergunta socrática para devolver a responsabilidade da decisão ao jogador.
    
    Dados da Janela Atual da Sessão:
    {dados_do_jogador}
    
    Escreva abaixo ÚNICA e EXCLUSIVAMENTE a sua pergunta socrática:
    """
    
    prompt_inicial = PromptTemplate.from_template(template_inicial)
    dados_str = json.dumps(estado_json, indent=2)
    
    print(f"🧠 Processando análise via Ollama (modelo: {modelo})... Aguarde.")
    try:
        primeira_pergunta = (prompt_inicial | llm).invoke({"dados_do_jogador": dados_str}).strip()
    except Exception as e:
        print(f"Falha na comunicação com o modelo local: {e}")
        return

    print("\n=== 🔮 FEEDBACK INICIAL DO MENTOR ===")
    print(primeira_pergunta)
    print("=======================================\n")
    
    # Inicia o histórico da conversa
    historico = f"Dados da Janela do Jogador:\n{dados_str}\n\nSua primeira pergunta ao jogador foi:\n{primeira_pergunta}\n"
    
    # Loop de interação
    while True:
        try:
            resposta_jogador = input("🗣️  Sua resposta (ou 'sair' para encerrar): ")
            if resposta_jogador.lower() in ['sair', 'exit', 'quit']:
                print("\nMentoria encerrada. Boa sorte nas mesas e foco no longo prazo!")
                break
                
            historico += f"\nO Jogador respondeu: {resposta_jogador}\n"
            
            template_interativo = """
            Você é um mentor de alta performance focado na psicologia de jogadores de Poker.
            
            Histórico da conversa até agora:
            {historico}
            
            Instruções:
            1. Avalie a resposta do jogador.
            2. Seja direto e incisivo. Dê um conselho curto OU faça uma nova pergunta reflexiva.
            3. Responda única e obrigatoriamente em Português do Brasil (PT-BR).
            
            Sua resposta:
            """
            
            prompt_interativo = PromptTemplate.from_template(template_interativo)
            
            print("🧠 O Mentor está analisando sua resposta...")
            nova_fala_mentor = (prompt_interativo | llm).invoke({"historico": historico}).strip()
            
            print("\n=== 🔮 MENTOR ===")
            print(nova_fala_mentor)
            print("===================\n")
            
            historico += f"\nVocê (Mentor) disse: {nova_fala_mentor}\n"
            
        except KeyboardInterrupt:
            print("\n\nMentoria interrompida. Boa sorte nas mesas!")
            break

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
    
    # Chama o motor da LangChain (agora em formato de Loop Interativo)
    iniciar_mentoria(estado_json, modelo=args.model)

if __name__ == "__main__":
    main()
