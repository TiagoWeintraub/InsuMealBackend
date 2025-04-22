from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from resources.food_history_resource import FoodHistoryResource
from schemas.food_history_schema import FoodHistoryCreate, FoodHistoryUpdate

router = APIRouter(prefix="/food_history", tags=["food_history"])

@router.post("/")
def create_food_history(data: FoodHistoryCreate, session: Session = Depends(get_session)):
    resource = FoodHistoryResource(session)
    return resource.create(data)

@router.get("/")
def read_food_history(session: Session = Depends(get_session)):
    resource = FoodHistoryResource(session)
    return resource.get_all()

@router.put("/{food_history_id}")
def update_food_history(food_history_id: int, data: FoodHistoryUpdate, session: Session = Depends(get_session)):
    resource = FoodHistoryResource(session)
    return resource.update(food_history_id, data)

@router.delete("/{food_history_id}")
def delete_food_history(food_history_id: int, session: Session = Depends(get_session)):
    resource = FoodHistoryResource(session)
    resource.delete(food_history_id)
    return {"msg": "FoodHistory eliminada exitosamente"}