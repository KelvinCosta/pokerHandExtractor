import json
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def auditar_com_rag_local(payload_json):
    """
    Função RAG: Consulta o ChromaDB para injetar heurísticas do Naigio antes de consultar o Llama 3.
    """
    
    # 1. Ligar o Motor de Busca (Rodando na CPU para não roubar VRAM do Llama 3)
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    
    # 2. Conectar ao Banco de Dados Vetorial (O seu Pendrive)
    vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    
    # O Retriever é o "Bibliotecário". Ele vai buscar os 2 blocos de texto mais relevantes.
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    # Transformamos os seus dados num texto para usar como "termo de pesquisa" na biblioteca
    dados_str = json.dumps(payload_json, indent=2)

    # 3. RECUPERAÇÃO (Retrieval): A IA vai à pasta buscar as regras que combinam com os seus dados!
    documentos_recuperados = retriever.invoke(dados_str)
    
    # Juntamos os textos recuperados numa única variável
    contexto_naigio = "\n\n".join([doc.page_content for doc in documentos_recuperados])

    # 4. O Prompt RAG (Agora com a Injeção de Contexto)
    template = """
    Você é um Sistema de Auditoria de Risco (Máquina). O seu usuário é um operador de Poker.
    A sua personalidade é SECA, CÍNICA, MILITAR e ROBÓTICA. Você NÃO tem emoções. Você não ri, não chora e não treme.
    Você NUNCA usa analogias (nada de barcos, pêndulos ou fogo).

    ========== CONHECIMENTO RECUPERADO (RAG) ==========
    {contexto}
    ===================================================

    ========== DADOS DA SESSÃO ==========
    {dados_do_jogador}
    =====================================

    FORMATO OBRIGATÓRIO DE RESPOSTA (Siga estritamente este formato, sem introduções ou saudações como "Meu jogador"):

    [DIAGNÓSTICO TÉCNICO]: (Descreva o erro ou vazamento em 1 frase curta baseada nos dados)
    [REGRA VIOLADA]: (Cite a regra dos Manuais de Operação do Naigio que não está sendo seguida)
    [AÇÃO EXIGIDA]: (Faça UMA única pergunta socrática, seca e direta, exigindo explicação do operador)
    """
    
    # Você tem uma RTX 3060 de 12GB! Sobra VRAM. Voltamos para o Llama 3 (O melhor).
    llm = OllamaLLM(model="llama3", num_ctx=4096)
    
    prompt = PromptTemplate.from_template(template)

    chain = prompt | llm

    print("📚 Consultando os manuais do Naigio no ChromaDB...")
    print("🧠 Processando análise via Ollama... Aguarde.")
    
    # Injetamos tanto o contexto (textos) quanto os dados (JSON) no Llama 3
    resposta = chain.invoke({
        "contexto": contexto_naigio,
        "dados_do_jogador": dados_str
    })

    return resposta

# --- TESTE DA FUNÇÃO ---
if __name__ == "__main__":
    # Vamos forçar um JSON que aciona o "Modo de Reversão" do seu Tilt
    json_teste_tilt = {
        "current_session_profit": -5.50, # Passou de -1 Buy-in! (Gatilho de Tilt)
        "current_agressiveness": 0.45,
        "showdown_frequency": 0.25,
        "consecutive_losses": 3,
        "context_window_info": {"num_hands_analyzed": 20, "hero_name": "Hero"}
    }
    
    alerta_na_tela = auditar_com_rag_local(json_teste_tilt)
    
    print("\n=== 🔮 ALERTA DO AGENTE RAG ===")
    print(alerta_na_tela)
    print("=================================\n")
    
    # === LOOP INTERATIVO ===
    llm = OllamaLLM(model="llama3", num_ctx=4096)
    historico = f"Sua primeira pergunta ao jogador foi:\n{alerta_na_tela}\n"
    
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
            1. Avalie a resposta do jogador com base na sua postura de Tech Lead Frio e Analítico.
            2. Seja direto e incisivo. Dê um conselho curto OU faça uma nova pergunta reflexiva.
            3. Responda única e obrigatoriamente em Português do Brasil (PT-BR).
            
            Sua resposta:
            """
            
            from langchain_core.prompts import PromptTemplate
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