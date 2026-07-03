import json
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def iniciar_auditoria_continua(payload_json):
    """
    Função RAG Interativa: Mantém o RAG e a personalidade rígida durante TODA a conversa.
    """
    print("📚 Consultando os manuais do Naigio no ChromaDB...")
    
    # 1. Ligar o Motor RAG
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    
    dados_str = json.dumps(payload_json, indent=2)
    documentos_recuperados = retriever.invoke(dados_str)
    contexto_naigio = "\n\n".join([doc.page_content for doc in documentos_recuperados])

    # 2. O Prompt Estrito (Usado tanto na 1ª resposta quanto no loop)
    template_auditoria = """
    [DIRETRIZ DO SISTEMA]: Você é um Sistema de Auditoria de Risco (Máquina). O seu usuário é um operador de Poker.
    A sua personalidade é SECA, CÍNICA, MILITAR e ROBÓTICA. Você NÃO tem emoções. Você não ri, não chora e não dá conselhos de vida.
    Você NUNCA usa analogias. PROIBIDO usar saudações como "Meu jogador", "Entendi", ou nomes próprios.

    [DIRETRIZ DE ESCALADA]: Se o operador responder com deboche, ignorância ("não sei"), ou se recusar a justificar matematicamente, decrete "Falha Cognitiva Crítica (Tilt Severo)".

    ========== CONHECIMENTO RECUPERADO (RAG) ==========
    {contexto}
    ===================================================

    ========== DADOS DA SESSÃO ==========
    {dados_do_jogador}
    =====================================

    ========== HISTÓRICO DA CONVERSA ==========
    {historico}
    ===========================================

    FORMATO OBRIGATÓRIO DE RESPOSTA (Siga rigorosamente as chaves abaixo):

    [INFORMAÇÃO DO SISTEMA]: (Se o operador fez uma pergunta direta ou pediu um dado, responda a ele aqui com o dado frio e exato. Se ele não fez pergunta, escreva apenas "N/A").
    [DIAGNÓSTICO TÉCNICO]: (Se for a 1ª mensagem, aponte os erros nos DADOS. A partir da 2ª, avalie a resposta do operador de forma cínica e crua em 1 frase).
    [AÇÃO EXIGIDA]: (Faça UMA única pergunta socrática, seca e direta).
    """
    
    prompt = PromptTemplate.from_template(template_auditoria)
    llm = OllamaLLM(model="llama3")

    # Histórico inicial
    historico_chat = "Auditoria iniciada. Analise os dados e faça a primeira cobrança."
    
    print("🧠 Processando análise via Ollama... Aguarde.\n")
    
    # --- PRIMEIRA INTERAÇÃO ---
    resposta_ia = (prompt | llm).invoke({
        "contexto": contexto_naigio,
        "dados_do_jogador": dados_str,
        "historico": historico_chat
    }).strip()
    
    print("=== 🔮 ALERTA DO AGENTE RAG ===")
    print(resposta_ia)
    print("=================================\n")
    
    historico_chat = f"Auditor Máquina: {resposta_ia}\n"

    # --- LOOP DE CONVERSA ---
    while True:
        try:
            resposta_jogador = input("🗣️  Sua resposta (ou 'sair' para encerrar): ")
            
            if resposta_jogador.lower() in ['sair', 'exit', 'quit']:
                print("\n[SISTEMA]: Auditoria encerrada. Stop-loss mantido. Desligando.")
                break
                
            historico_chat += f"Operador: {resposta_jogador}\n"
            
            print("🧠 Recalculando desvio de rota... Aguarde.\n")
            
            nova_resposta_ia = (prompt | llm).invoke({
                "contexto": contexto_naigio,
                "dados_do_jogador": dados_str,
                "historico": historico_chat
            }).strip()
            
            print("=== 🔮 ALERTA DO AGENTE RAG ===")
            print(nova_resposta_ia)
            print("=================================\n")
            
            historico_chat += f"Auditor Máquina: {nova_resposta_ia}\n"
            
        except KeyboardInterrupt:
            print("\n\n[SISTEMA]: Auditoria interrompida no terminal.")
            break

# --- TESTE DA FUNÇÃO ---
if __name__ == "__main__":
    json_teste_tilt = {
        "current_session_profit": -5.50,
        "current_agressiveness": 0.45,
        "showdown_frequency": 0.25,
        "consecutive_losses": 3,
        "context_window_info": {"num_hands_analyzed": 20, "hero_name": "Hero"}
    }
    iniciar_auditoria_continua(json_teste_tilt)