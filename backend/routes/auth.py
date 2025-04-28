from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from database import get_session
from models.user import User
from schemas.user_schema import UserCreate, LoginInput, UserRead
from resources.user_resource import UserResource

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead)
async def register(data: UserCreate, session: Session = Depends(get_session)):
    try:
        existing = UserResource.get_user_by_email(data.email, session)
        if existing:
            raise HTTPException(status_code=400, detail="Email ya registrado")

        user = UserResource.create_user(data, session)
        return user

    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al registrar el usuario") from e



@router.post("/login")
async def login(data: LoginInput, session: Session = Depends(get_session)):
    try:
        return UserResource.login_user(data, session)
    except HTTPException as e:
        raise e
