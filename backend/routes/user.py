from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List

from database import get_session
from auth.dependencies import get_current_user
from models.user import User
from schemas.user_schema import UserRead, UserUpdate, PasswordChange
from resources.user_resource import UserResource

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/get/users", response_model=List[UserRead]) # Trae todos los usuarios
def get_all(session: Session = Depends(get_session)):
    return UserResource.get_all_users(session)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/put", response_model=UserRead)
def update(data: UserUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return UserResource.update_user(data, current_user, session)


@router.delete("/delete", status_code=204)
def delete(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    UserResource.delete_user(current_user, session)

@router.delete("/delete_by_id/{user_id}", status_code=200)
def delete_user_by_id(user_id: int, session: Session = Depends(get_session)):
    return UserResource.delete_by_id(user_id, session)

@router.post("/change-password")
def change_pass(data: PasswordChange, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return UserResource.change_password(data, current_user, session)
