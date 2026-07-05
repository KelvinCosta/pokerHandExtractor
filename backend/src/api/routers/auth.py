import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.database.models import User
from src.core.security import get_password_hash, verify_password, create_access_token
from src.api.schemas.auth import UserCreate, UserLogin, Token

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Email já cadastrado"
        )
    
    new_user = User(
        id=str(uuid.uuid4()),
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.id})
    return {"access_token": access_token, "token_type": "bearer", "user_id": new_user.id}

from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login", response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Swagger Auth envia os dados como form_data.username e form_data.password
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}
