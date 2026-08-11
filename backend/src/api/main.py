import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa as tabelas do SQLite no boot
    print("[INFO] Inicializando Banco de Dados...")
    init_db()
    yield
    print("[INFO] Servidor encerrado.")

from src.api.routers import dashboard, auth, etl, team

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

app.include_router(auth.router)
app.include_router(etl.router)
app.include_router(dashboard.router)
app.include_router(team.router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "API rodando e pronta!"}
