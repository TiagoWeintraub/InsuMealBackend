from sqlmodel import SQLModel, Field
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from backend.models.user import User
from backend.auth.jwt_handler import create_access_token
from backend.auth.dependencies import get_current_user
from backend.database import get_session  
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/users", tags=["Users"])

### SCHEMAS ###

class UserCreate(BaseModel):
    name: str
    lastName: str
    email: EmailStr
    password: str
    idClinicalData: int


class UserRead(BaseModel):
    id: int
    name: str
    lastName: str
    email: EmailStr


class UserUpdate(BaseModel):
    name: str
    lastName: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


### ENDPOINTS ###

@router.post("/", response_model=UserRead)
def create_user(data: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    user = User.from_json(data.dict())
    session.add(user)
    session.commit()
    session.refresh(user)
    return user.to_json()


@router.get("/", response_model=List[UserRead])
def get_users(session: Session = Depends(get_session)):
    return [user.to_json() for user in session.exec(select(User)).all()]


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user.to_json()


@router.put("/", response_model=UserRead)
def update_user(data: UserUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    current_user.name = data.name
    current_user.lastName = data.lastName
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user.to_json()


@router.delete("/", status_code=204)
def delete_user(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    session.delete(current_user)
    session.commit()


@router.post("/change-password")
def change_password(data: PasswordChange, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not current_user.validate_pass(data.old_password):
        raise HTTPException(status_code=403, detail="Contraseña actual incorrecta")

    current_user.plain_password = data.new_password
    session.add(current_user)
    session.commit()
    return {"msg": "Contraseña actualizada exitosamente"}


@router.post("/login")
def login(data: LoginInput, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user or not user.validate_pass(data.password):
        raise HTTPException(status_code=400, detail="Credenciales inválidas")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
    