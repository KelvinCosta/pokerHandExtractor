import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    players = relationship("Player", back_populates="user")
    teams = relationship("TeamMember", back_populates="user")
    invitations = relationship("Invitation", back_populates="invitee", foreign_keys="[Invitation.invitee_id]")

class Team(Base):
    __tablename__ = 'teams'
    id = Column(String, primary_key=True)
    name = Column(String)
    owner_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("TeamMember", back_populates="team")
    invitations = relationship("Invitation", back_populates="team")

class TeamMember(Base):
    __tablename__ = 'team_members'
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"))
    user_id = Column(String, ForeignKey("users.id"))
    role = Column(String) # "admin", "player"
    status = Column(String, default="active") # "active", "inactive"
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)
    
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="teams")

class Invitation(Base):
    __tablename__ = 'invitations'
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"))
    invitee_id = Column(String, ForeignKey("users.id"))
    status = Column(String, default="pending") # pending, accepted, declined
    created_at = Column(DateTime, default=datetime.utcnow)
    
    team = relationship("Team", back_populates="invitations")
    invitee = relationship("User", back_populates="invitations", foreign_keys=[invitee_id])

class Player(Base):
    __tablename__ = 'player'
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="players")

    snapshots = relationship("PokerStatsSnapshot", back_populates="player")
    sessions = relationship("AuditSession", back_populates="player")


class PokerStatsSnapshot(Base):
    __tablename__ = 'poker_stats_snapshot'
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String, ForeignKey('player.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    hands_played = Column(Integer)
    win_rate_bb100 = Column(Float)
    vpip = Column(Float)
    pfr = Column(Float)
    profit_bb = Column(Float)
    max_session_downswing_bb = Column(Float)
    current_losing_streak_sessions = Column(Integer)
    
    raw_state_json = Column(Text, nullable=True) # Payload completo extraído do DuckDB

    player = relationship("Player", back_populates="snapshots")


class AuditSession(Base):
    __tablename__ = 'audit_session'
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String, ForeignKey('player.id'))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    status_variancia = Column(String)
    nivel_gravidade = Column(Integer)
    raw_diagnostic_json = Column(Text, nullable=True) # Payload completo do Agente 1 (Red flags etc)
    
    admitiu_erro = Column(Boolean, nullable=True)
    nivel_negacao = Column(Integer, nullable=True)
    conclusao_entrevista = Column(Text, nullable=True)
    recomendacao_coach = Column(Text, nullable=True)

    player = relationship("Player", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = 'chat_message'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('audit_session.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    role = Column(String) # 'user' ou 'assistant'
    content = Column(Text)

    session = relationship("AuditSession", back_populates="messages")

class HandAnalysisRecord(Base):
    __tablename__ = 'hand_analyses'
    id = Column(String, primary_key=True)
    hand_id = Column(String, index=True, unique=True)
    raw_analysis = Column(Text)
    agent_version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class HandNoteRecord(Base):
    __tablename__ = 'hand_notes'
    id = Column(String, primary_key=True)
    hand_id = Column(String, index=True)
    user_id = Column(String, index=True)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ==========================================
# UTILITÁRIOS (HELPERS DE REPOSITÓRIO)
# ==========================================

engine = None
SessionLocal = None

def init_db(db_path="sqlite:///auditoria.db"):
    global engine, SessionLocal
    engine = create_engine(db_path, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine

def get_session():
    if SessionLocal is None:
        init_db()
    return SessionLocal()

def create_audit_session(player_id, initial_diagnostic, stats=None):
    """
    Cria a sessão de auditoria e garante que o jogador existe no banco.
    Opcionalmente (recomendado), recebe o objeto de estatísticas atual (PlayerStats)
    para salvar uma fotografia do comportamento exato (PokerStatsSnapshot) que originou a auditoria.
    Retorna o ID numérico da sessão gerada.
    """
    db = get_session()
    
    # 1. Garante a existência do Player
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        player = Player(id=player_id, name=player_id)
        db.add(player)
        db.commit()
        
    # 2. Registra o Snapshot das Estatísticas (se fornecido)
    if stats:
        snapshot = PokerStatsSnapshot(
            player_id=player_id,
            hands_played=stats.global_stats.hands_played,
            win_rate_bb100=stats.global_stats.win_rate_bb100,
            vpip=stats.global_stats.vpip,
            pfr=stats.global_stats.pfr,
            profit_bb=stats.global_stats.profit_bb,
            max_session_downswing_bb=stats.behavioral_triggers.max_session_downswing_bb,
            current_losing_streak_sessions=stats.behavioral_triggers.current_losing_streak_sessions,
            raw_state_json=stats.model_dump_json() # Salva o payload completo
        )
        db.add(snapshot)
        
    # 3. Cria a sessão de auditoria vinculada ao Laudo Inicial do Agente 1
    audit_session = AuditSession(
        player_id=player_id,
        status_variancia=initial_diagnostic.status_variancia,
        nivel_gravidade=initial_diagnostic.nivel_gravidade,
        raw_diagnostic_json=initial_diagnostic.model_dump_json() # Salva o payload completo
    )
    db.add(audit_session)
    db.commit()
    db.refresh(audit_session)
    
    session_id = audit_session.id
    db.close()
    
    return session_id


def save_chat_message(session_id, role, content):
    """
    Salva uma mensagem individual atrelada à sessão no banco. (Write-Ahead Log)
    Role deve ser 'user' ou 'assistant'.
    """
    db = get_session()
    msg = ChatMessage(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.close()


def complete_audit_session(session_id, final_report):
    """
    Puxa a sessão de auditoria e salva o Laudo Final (Agente Final), além de datar a conclusão.
    """
    db = get_session()
    audit_session = db.query(AuditSession).filter(AuditSession.id == session_id).first()
    
    if audit_session:
        audit_session.completed_at = datetime.utcnow()
        audit_session.admitiu_erro = final_report.admitiu_erro
        audit_session.nivel_negacao = final_report.nivel_negacao
        audit_session.conclusao_entrevista = final_report.conclusao_entrevista
        audit_session.recomendacao_coach = final_report.recomendacao_coach
        db.commit()
        
    db.close()


# Execução rápida para criar as tabelas no terminal
if __name__ == "__main__":
    from pathlib import Path
    db_file_path = Path(__file__).resolve().parent.parent.parent / "auditoria.db"
    db_uri = f"sqlite:///{db_file_path}"
    
    init_db(db_uri)
    print(f"✅ Banco de dados 'auditoria.db' criado com sucesso usando SQLAlchemy!")
    print(f"Caminho: {db_file_path}")
