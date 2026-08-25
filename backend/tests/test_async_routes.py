import inspect
import sys
import os

# Adiciona a raiz do backend ao path do Python para evitar ModuleNotFoundError
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.routers import etl, dashboard

def test_heavy_routes_must_not_be_async():
    """
    Testa se as rotas que realizam processamento pesado de CPU (Polars)
    ou I/O bloqueante (arquivos, SQLAlchemy sem await) não estão usando `async def`.
    O FastAPI bloquearia o Event Loop caso essas rotas fossem `async def`.
    """
    routers_to_check = [etl.router, dashboard.router]
    
    async_routes_found = []
    
    for router in routers_to_check:
        for route in router.routes:
            # Verifica se o endpoint da rota é uma corrotina (async def)
            if inspect.iscoroutinefunction(route.endpoint):
                async_routes_found.append(f"{route.methods} {route.path} -> {route.endpoint.__name__}")
                
    # Se a lista não estiver vazia, o teste falha mostrando quem violou a regra.
    # Note que rotas de websocket ou endpoints puramente assíncronos que usam `await` 
    # podem ser permitidos, mas nesses dois routers específicos, nossa regra de negócio 
    # proíbe rotas async devido ao Polars.
    assert not async_routes_found, (
        "As seguintes rotas não podem ser `async def` devido ao risco de bloquear o Event Loop "
        f"com I/O e CPU bounds do Polars: {async_routes_found}"
    )
