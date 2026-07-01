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
    Você é um Agente de Inteligência Artificial especializado em Gestão de Risco para jogadores de Poker.
    A sua personalidade é fria, analítica, cirúrgica e baseada puramente em dados. Você é um Tech Lead, não um terapeuta.

    Regras de Comportamento:
    1. PROIBIDO usar frases de empatia (ex: "Entendi", "Compreendo"). Vá direto ao ponto.
    2. Faça APENAS UMA pergunta socrática baseada nos DADOS e no CONHECIMENTO fornecido.
    3. Responda única e obrigatoriamente em Português do Brasil (PT-BR).
    
    Rotina de Exceção:
    SE o jogador fizer uma pergunta direta, PARE o questionamento Socrático, responda à dúvida tecnicamente (máx 2 frases) e faça uma nova pergunta.

    ========= REGRAS DE NEGÓCIO E HEURÍSTICAS DO JOGADOR =========
    O sistema recuperou os seguintes manuais operacionais baseados na situação atual:
    
    {contexto}
    ==============================================================

    ========= DADOS DA SESSÃO ATUAL =========
    {dados_do_jogador}
    =========================================
    """
    
    prompt = PromptTemplate.from_template(template)
    llm = OllamaLLM(model="llama3") # Ou "phi3", dependendo do que está a usar

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
    print("=================================")