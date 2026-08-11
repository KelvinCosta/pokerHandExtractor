import uvicorn
import webview
import threading
import sys
import time
import os
import traceback
from src.api.main import app

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
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write("\n--- Iniciando PokerApp ---\n")

    # Inicia o FastAPI em uma thread secundária
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Dá 1 segundo para o servidor subir antes de mostrar a janela
    time.sleep(1)
    
    # Abre a janela nativa com pywebview
    webview.create_window("Poker Analytics Dashboard", "http://127.0.0.1:8000", width=1280, height=800)
    webview.start(debug=True)
    
    # Quando o usuário fechar a janela, o processo é encerrado limpando a porta
    sys.exit(0)
