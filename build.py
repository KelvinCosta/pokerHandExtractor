import os
import subprocess
import shutil
import sys
import argparse
from pathlib import Path

def run_command(command, cwd=None):
    print(f"Executando: {command} em {cwd or os.getcwd()}")
    process = subprocess.Popen(command, shell=True, cwd=cwd)
    process.wait()
    if process.returncode != 0:
        print(f"Erro ao executar: {command}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Build script for PokerApp")
    parser.add_argument("--skip-frontend", action="store_true", help="Pula o build do frontend (Next.js)")
    parser.add_argument("--skip-deps", action="store_true", help="Pula a instalação de dependências (pnpm e pip)")
    parser.add_argument("--onedir", action="store_true", help="Gera uma pasta com os arquivos em vez de um único .exe (Build muito mais rápido e inicialização instantânea do app)")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent
    frontend_dir = root_dir / "frontend"
    backend_dir = root_dir / "backend"
    
    # 1. Build do Frontend
    if not args.skip_frontend:
        print("\n=== Compilando Frontend (Next.js) ===")
        if not args.skip_deps:
            run_command("pnpm install", cwd=str(frontend_dir))
        run_command("pnpm run build", cwd=str(frontend_dir))
    else:
        print("\n=== Pulando Build do Frontend ===")
    
    frontend_out = frontend_dir / "out"
    if not frontend_out.exists():
        print("Erro: A pasta frontend/out não foi gerada!")
        sys.exit(1)
        
    # 2. Instalar dependências de build no Backend
    if not args.skip_deps:
        print("\n=== Instalando PyInstaller e PyWebview ===")
        run_command(f'"{sys.executable}" -m pip install pyinstaller pywebview', cwd=str(backend_dir))
    else:
        print("\n=== Pulando Instalação de Dependências ===")
    
    # 3. Empacotar com PyInstaller
    print("\n=== Empacotando Backend + Frontend (PyInstaller) ===")
    
    # Monta o comando do pyinstaller
    build_type = "--onedir" if args.onedir else "--onefile"
    pyinstaller_command = (
        f'"{sys.executable}" -m PyInstaller --name PokerApp --clean --noconfirm --windowed {build_type} '
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
        '--hidden-import "src.api.main" '
        'boot.py'
    )
    
    # Cria um script de boot
    boot_script = backend_dir / "boot.py"
    with open(boot_script, "w", encoding="utf-8") as f:
        f.write('''import webview
import threading
import sys
import time
import os
import traceback
import urllib.request

# Configuração de Logs de Erro
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
log_path = os.path.join(app_dir, "PokerApp_error.log")

class StreamToLogger(object):
    def __init__(self, original_stream):
        self.original_stream = original_stream
    def write(self, buf):
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(buf)
        try:
            self.original_stream.write(buf)
        except UnicodeEncodeError:
            self.original_stream.write(buf.encode('ascii', errors='replace').decode('ascii'))
    def flush(self):
        self.original_stream.flush()
    def isatty(self):
        return False
    def __getattr__(self, name):
        return getattr(self.original_stream, name)

sys.stdout = StreamToLogger(sys.stdout)
sys.stderr = StreamToLogger(sys.stderr)

def exception_handler(exctype, value, tb):
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write("".join(traceback.format_exception(exctype, value, tb)))
    sys.__excepthook__(exctype, value, tb)
sys.excepthook = exception_handler

def start_server():
    # Imports pesados movidos para cá para não atrasar a tela de carregamento
    import uvicorn
    from src.api.main import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

def check_and_redirect(window):
    url = "http://127.0.0.1:8000"
    while True:
        try:
            with urllib.request.urlopen(url) as response:
                if response.getcode() == 200:
                    break
        except Exception:
            pass
        time.sleep(0.5)
    # Redireciona a janela para a aplicação
    window.load_url(url)

if __name__ == "__main__":
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write("\\n--- Iniciando PokerApp ---\\n")

    loading_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Carregando PokerApp...</title>
        <style>
            body {
                background-color: #0f172a;
                color: #f8fafc;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                font-family: system-ui, -apple-system, sans-serif;
            }
            .loader {
                border: 4px solid #334155;
                border-top: 4px solid #3b82f6;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin-bottom: 24px;
            }
            h2 { font-weight: 500; margin-bottom: 8px; }
            p { color: #94a3b8; margin: 0; }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="loader"></div>
        <h2>Iniciando Poker Analytics Dashboard</h2>
        <p>Carregando base de dados e componentes em memória...</p>
    </body>
    </html>
    """

    # Abre a janela nativa imediatamente com a tela de carregamento HTML
    window = webview.create_window("Poker Analytics Dashboard", html=loading_html, width=1280, height=800)

    # Inicia o FastAPI em uma thread secundária
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Inicia o monitor do servidor para redirecionar quando estiver pronto
    monitor_thread = threading.Thread(target=check_and_redirect, args=(window,), daemon=True)
    monitor_thread.start()
    
    # Bloqueia o processo principal aqui até a janela ser fechada
    webview.start(debug=False)
    
    # Quando o usuário fechar a janela, o processo é encerrado
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
    if args.onedir:
        print(f"O aplicativo está disponível em: {backend_dir / 'dist' / 'PokerApp'}")
        print("Basta acessar a pasta e executar o PokerApp.exe!")
    else:
        print(f"O executável está disponível em: {backend_dir / 'dist' / 'PokerApp.exe'}")
        print("Basta executar esse arquivo! Uma janela de aplicativo nativa se abrirá.")

if __name__ == "__main__":
    main()
