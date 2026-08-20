from pydantic import BaseModel, ConfigDict
from typing import Optional

class AuditStartRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    # Parâmetros de filtro para puxar o stats do jogador a ser auditado
    hero_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    session_id: str
    message: str

class AuditCompleteRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    session_id: str
