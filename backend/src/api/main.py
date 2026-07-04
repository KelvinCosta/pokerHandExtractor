import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.dashboard.data_loader import load_data, load_tournaments

# Armazenamento Global (Substitui o st.cache_data do Streamlit)
class AppState:
    df_hands = None
    df_tournaments = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executado ao ligar o servidor (Startup)
    print("🚀 Carregando Datalake em memória...")
    try:
        AppState.df_hands = load_data()
        AppState.df_tournaments = load_tournaments()
        print("✅ Datalake carregado com sucesso!")
    except Exception as e:
        print(f"⚠️ Erro ao carregar Datalake: {e}")
    
    yield
    
    # Executado ao desligar o servidor (Shutdown)
    print("🛑 Servidor encerrado. Limpando memória.")
    AppState.df_hands = None
    AppState.df_tournaments = None

from src.api.routers import dashboard

app = FastAPI(
    title="Poker Analytics API",
    description="SaaS B2B Poker Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração de CORS para permitir requisições do React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "API rodando e pronta!"}
