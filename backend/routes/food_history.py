from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from resources.food_history_resource import FoodHistoryResource
from schemas.food_history_schema import FoodHistoryCreate, FoodHistoryUpdate
from auth.dependencies import get_current_user 

router = APIRouter(prefix="/food_history", tags=["food_history"])

@router.get("/")
async def read_food_history(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = FoodHistoryResource(session)
    return resource.get_all()

@router.put("/{food_history_id}")
async def update_food_history(food_history_id: int, data: FoodHistoryUpdate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = FoodHistoryResource(session)
    return resource.update(food_history_id, data)
