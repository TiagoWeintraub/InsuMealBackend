from fastapi import APIRouter, Depends
from sqlmodel import Session

from auth.dependencies import get_current_admin
from database import get_session
from models.user import User
from resources.user_resource import UserResource
from schemas.user_schema import AdminUserRead, AdminUserUpdate, UserUsageSummary

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.put("/users/{user_id}", response_model=AdminUserRead)
async def admin_update_user(
    user_id: int,
    data: AdminUserUpdate,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    return UserResource.admin_update_user(user_id, data, session)


@router.delete("/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    return UserResource.delete_by_id(user_id, session)


@router.get("/users/{user_id}/usage", response_model=UserUsageSummary)
async def admin_get_user_usage(
    user_id: int,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    return UserResource.get_user_usage_summary(user_id, session)
