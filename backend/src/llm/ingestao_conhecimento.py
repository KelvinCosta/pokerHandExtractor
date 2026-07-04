import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def criar_banco_vetorial():
    print("⏳ Carregando os Manuais de Operação do Naigio...")
    
    # 1. Carregar os documentos da sua pasta de docs (Ajuste o caminho se necessário)
    caminho_docs = './src/llm/docs'
    loader = DirectoryLoader(
        caminho_docs, 
        glob="**/*.md", 
        loader_cls=TextLoader, 
        loader_kwargs={'encoding': 'utf-8'}
    )
    documentos = loader.load()
    
    print(f"📄 {len(documentos)} documentos lidos.")

    # 2. Quebrar os textos em Chunks (Pedaços menores para a IA digerir melhor)
    # 500 caracteres por pedaço, com 50 de sobreposição para não cortar frases ao meio
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documentos)
    
    print(f"🧩 Documentos quebrados em {len(chunks)} fragmentos lógicos.")

    # 3. O Motor de Embeddings (O Tradutor de Texto para Matemática)
    # Vamos usar um modelo gratuito e ultra-rápido da HuggingFace (Roda local na CPU)
    print("🧠 Baixando/Iniciando modelo de embeddings (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # 4. Criar e Salvar o Banco Vetorial (ChromaDB)
    pasta_banco = "./chroma_db"
    
    print("💾 Vetorizando dados e salvando no ChromaDB...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=pasta_banco
    )
    
    print(f"✅ Sucesso! Conhecimento do 'Naigio' salvo na pasta '{pasta_banco}'.")

if __name__ == "__main__":
    criar_banco_vetorial()