import os
import subprocess
import shutil
import sys
from pathlib import Path

def run_command(command, cwd=None):
    print(f"Executando: {command} em {cwd or os.getcwd()}")
    process = subprocess.Popen(command, shell=True, cwd=cwd)
    process.wait()
    if process.returncode != 0:
        print(f"Erro ao executar: {command}")
        sys.exit(1)

def main():
    root_dir = Path(__file__).resolve().parent
    frontend_dir = root_dir / "frontend"
    backend_dir = root_dir / "backend"
    
    # 1. Build do Frontend
    print("\n=== Compilando Frontend (Next.js) ===")
    run_command("pnpm install", cwd=str(frontend_dir))
    run_command("pnpm run build", cwd=str(frontend_dir))
    
    frontend_out = frontend_dir / "out"
    if not frontend_out.exists():
        print("Erro: A pasta frontend/out não foi gerada!")
        sys.exit(1)
        
    # 2. Instalar dependências de build no Backend
    print("\n=== Instalando PyInstaller e PyWebview ===")
    run_command(f'"{sys.executable}" -m pip install pyinstaller pywebview', cwd=str(backend_dir))
    
    # 3. Empacotar com PyInstaller
    print("\n=== Empacotando Backend + Frontend (PyInstaller) ===")
    
    # Monta o comando do pyinstaller
    # Adicionamos a pasta do frontend embutida, e incluímos as dependências escondidas do uvicorn/fastapi
    pyinstaller_command = (
        f'"{sys.executable}" -m PyInstaller --name PokerApp --clean --noconfirm --windowed '
        '--add-data "../frontend/out;frontend_out" '
        '--hidden-import "uvicorn.logging" '
        '--hidden-import "uvicorn.loops" '
        '--hidden-import "uvicorn.loops.auto" '
        '--hidden-import "uvicorn.protocols" '
        '--hidden-import "uvicorn.protocols.http" '
        '--hidden-import "uvicorn.protocols.http.auto" '
        '--hidden-import "uvicorn.protocols.websockets" '
        '--hidden-import "uvicorn.protocols.websockets.auto" '
        '--hidden-import "uvicorn.lifespan" '
        '--hidden-import "uvicorn.lifespan.on" '
        '--hidden-import "webview" '
        'boot.py'
    )
    
    # Cria um script de boot
    boot_script = backend_dir / "boot.py"
    with open(boot_script, "w", encoding="utf-8") as f:
        f.write('''import uvicorn
import webview
import threading
import sys
import time
from src.api.main import app

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    # Inicia o FastAPI em uma thread secundária
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Dá 1 segundo para o servidor subir antes de mostrar a janela
    time.sleep(1)
    
    # Abre a janela nativa com pywebview
    webview.create_window("Poker Analytics Dashboard", "http://127.0.0.1:8000", width=1280, height=800)
    webview.start()
    
    # Quando o usuário fechar a janela, o processo é encerrado limpando a porta
    sys.exit(0)
''')
    
    run_command(pyinstaller_command, cwd=str(backend_dir))
    
    # Limpa o arquivo de boot temporário e o .spec
    if boot_script.exists():
        boot_script.unlink()
    
    spec_file = backend_dir / "PokerApp.spec"
    if spec_file.exists():
        spec_file.unlink()
        
    print("\n=== Build Concluída com Sucesso! ===")
    print(f"O executável está disponível em: {backend_dir / 'dist' / 'PokerApp' / 'PokerApp.exe'}")
    print("Basta executar esse arquivo! Uma janela de aplicativo nativa se abrirá.")

if __name__ == "__main__":
    main()
