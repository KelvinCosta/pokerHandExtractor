from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid

from src.database.session import get_db
from src.database.models import User, Team, TeamMember, Invitation
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/api/team", tags=["Team Management"])

class TeamCreate(BaseModel):
    name: str

class InviteCreate(BaseModel):
    email: EmailStr

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_team(team: TeamCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Cria uma nova equipe e define o criador como Admin (owner)"""
    new_team = Team(
        id=str(uuid.uuid4()),
        name=team.name,
        owner_id=current_user.id
    )
    db.add(new_team)
    
    # Adiciona o owner como membro ativo e admin
    membership = TeamMember(
        id=str(uuid.uuid4()),
        team_id=new_team.id,
        user_id=current_user.id,
        role="admin",
        status="active"
    )
    db.add(membership)
    db.commit()
    db.refresh(new_team)
    return {"message": "Equipe criada com sucesso", "team_id": new_team.id, "team_name": new_team.name}

@router.get("/")
def list_teams(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Lista as equipes que o usuário faz parte e seus membros ativos"""
    memberships = db.query(TeamMember).filter(TeamMember.user_id == current_user.id, TeamMember.status == "active").all()
    
    result = []
    for mem in memberships:
        team = mem.team
        team_data = {
            "team_id": team.id,
            "name": team.name,
            "role": mem.role,
            "members": [
                {
                    "user_id": m.user.id,
                    "email": m.user.email,
                    "role": m.role,
                    "joined_at": m.joined_at
                }
                for m in team.members if m.status == "active"
            ]
        }
        result.append(team_data)
        
    return result

@router.post("/{team_id}/invite", status_code=status.HTTP_200_OK)
def invite_player(team_id: str, invite_data: InviteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Convida um jogador para o time por email. Trava de exclusividade aplicada."""
    
    # 1. Verifica se o time existe e se o usuário atual é admin nele
    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.role == "admin",
        TeamMember.status == "active"
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Você não tem permissão para convidar pessoas para este time")
        
    # 2. Busca o usuário pelo e-mail
    invitee = db.query(User).filter(User.email == invite_data.email).first()
    if not invitee:
        raise HTTPException(status_code=404, detail="Nenhum jogador encontrado com este e-mail")
        
    # 3. Trava de Exclusividade (O jogador já está ATIVO em algum time?)
    active_teams = db.query(TeamMember).filter(
        TeamMember.user_id == invitee.id,
        TeamMember.status == "active"
    ).first()
    
    if active_teams:
        raise HTTPException(status_code=400, detail="Este jogador já está ativo em outra equipe. A exclusividade impede novos convites.")
        
    # 4. Evita convites duplicados para o mesmo time
    existing_invite = db.query(Invitation).filter(
        Invitation.team_id == team_id,
        Invitation.invitee_id == invitee.id,
        Invitation.status == "pending"
    ).first()
    
    if existing_invite:
        raise HTTPException(status_code=400, detail="Este jogador já possui um convite pendente para este time.")
        
    new_invite = Invitation(
        id=str(uuid.uuid4()),
        team_id=team_id,
        invitee_id=invitee.id,
        status="pending"
    )
    db.add(new_invite)
    db.commit()
    
    return {"message": "Convite enviado com sucesso!"}

@router.get("/invitations")
def list_invitations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Lista todos os convites pendentes do usuário atual"""
    invites = db.query(Invitation).filter(
        Invitation.invitee_id == current_user.id,
        Invitation.status == "pending"
    ).all()
    
    return [
        {
            "invitation_id": inv.id,
            "team_id": inv.team.id,
            "team_name": inv.team.name,
            "invited_at": inv.created_at
        }
        for inv in invites
    ]

@router.post("/invitations/{invitation_id}/accept")
def accept_invitation(invitation_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Aceita um convite e recusa todos os outros"""
    invite = db.query(Invitation).filter(
        Invitation.id == invitation_id,
        Invitation.invitee_id == current_user.id,
        Invitation.status == "pending"
    ).first()
    
    if not invite:
        raise HTTPException(status_code=404, detail="Convite não encontrado ou já expirou")
        
    # Trava de Segurança Final (Vai que ele aceitou outro convite por outra aba?)
    active_teams = db.query(TeamMember).filter(TeamMember.user_id == current_user.id, TeamMember.status == "active").first()
    if active_teams:
        raise HTTPException(status_code=400, detail="Você já está ativo em outra equipe.")
        
    # Aceita este
    invite.status = "accepted"
    
    # Cria o TeamMember
    membership = TeamMember(
        id=str(uuid.uuid4()),
        team_id=invite.team_id,
        user_id=current_user.id,
        role="player",
        status="active"
    )
    db.add(membership)
    
    # Rejeita automaticamente todos os outros convites pendentes
    other_invites = db.query(Invitation).filter(
        Invitation.invitee_id == current_user.id,
        Invitation.status == "pending"
    ).all()
    
    for other in other_invites:
        other.status = "declined"
        
    db.commit()
    
    return {"message": f"Você entrou na equipe {invite.team.name} com sucesso!"}

@router.post("/{team_id}/fire/{user_id}")
def fire_player(team_id: str, user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Demite um jogador. Ele fica 'inactive' mas preserva os dados históricos (left_at)."""
    
    # Verifica se quem tá chamando é admin
    admin_check = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.role == "admin",
        TeamMember.status == "active"
    ).first()
    
    if not admin_check:
        raise HTTPException(status_code=403, detail="Você não tem permissão para demitir jogadores neste time")
        
    # Busca o membro a ser demitido
    target_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
        TeamMember.status == "active"
    ).first()
    
    if not target_member:
        raise HTTPException(status_code=404, detail="Jogador não encontrado na equipe ou já está inativo")
        
    if target_member.role == "admin" and target_member.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode demitir a si mesmo")
        
    # Executa a demissão preservando histórico
    target_member.status = "inactive"
    target_member.left_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Jogador desligado da equipe com sucesso. O histórico financeiro dele foi preservado para auditoria."}
