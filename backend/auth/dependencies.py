from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from auth.jwt_handler import decode_access_token
from models.user import User
from models.role import Role
from sqlmodel import Session, select
from database import get_session  # Tu función de sesión

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    user = session.exec(select(User).where(User.id == payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    role = session.get(Role, current_user.role_id)
    if not role or role.name != "admin":
        raise HTTPException(status_code=403, detail="Acceso restringido a administradores")
    return current_user
