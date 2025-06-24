from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from database import get_session
from resources.food_history_resource import FoodHistoryResource
from schemas.food_history_schema import FoodHistoryCreate, FoodHistoryUpdate, PaginatedResponse
from auth.dependencies import get_current_user 
from models.user import User

router = APIRouter(prefix="/food_history", tags=["food_history"])

# @router.get("/")
# async def read_food_history(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
#     resource = FoodHistoryResource(session)
#     return resource.get_all()

@router.get("/")
async def read_user_food_history_paginated(
    page: int = Query(1, ge=1, description="Número de página (empieza en 1)"),
    page_size: int = Query(10, ge=1, le=50, description="Elementos por página (máximo 50)"),
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
) -> PaginatedResponse:
    """
    Obtiene el historial de comidas del usuario actual con paginación.
    Retorna 10 elementos por página por defecto.
    """
    resource = FoodHistoryResource(session)
    return resource.get_user_meal_plates_paginated(current_user.id, page, page_size)

@router.put("/{food_history_id}")
async def update_food_history(food_history_id: int, data: FoodHistoryUpdate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = FoodHistoryResource(session)
    return resource.update(food_history_id, data)
