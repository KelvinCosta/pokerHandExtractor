from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
