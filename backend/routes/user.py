from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List

from database import get_session
from auth.dependencies import get_current_user
from models.user import User
from schemas.user_schema import UserRead, UserUpdate, PasswordChange
from resources.user_resource import UserResource

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=List[UserRead])
async def get_all(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return UserResource.get_all_users(session)


@router.get("/get_by_id/{user_id}", response_model=UserRead)
async def get_by_id(user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    user = UserResource.get_user_by_id(user_id, session)
    if not user:
        return {"message": "User not found"}
    return user

@router.get("/all", response_model=List[UserRead])
async def get_all_users(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return UserResource.get_all_users(session)

# @router.put("/put", response_model=UserRead) No sé si es necesario
# def update(data: UserUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
#     return UserResource.update_user(data, current_user, session)

@router.delete("/delete", status_code=204)
async def delete(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    UserResource.delete_user(current_user, session)

@router.delete("/delete_by_id/{user_id}", status_code=200)
async def delete_user_by_id(user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return UserResource.delete_by_id(user_id, session)

@router.post("/change-password")
async def change_pass(data: PasswordChange, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return UserResource.change_password(data, current_user, session)