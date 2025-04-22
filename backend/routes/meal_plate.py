from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from resources.meal_plate_resource import MealPlateResource
from schemas.meal_plate_schema import MealPlateCreate, MealPlateUpdate

router = APIRouter(prefix="/meal_plate", tags=["meal_plate"])

@router.post("/")
def create_meal_plate(data: MealPlateCreate, session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.create(data)

@router.get("/")
def read_meal_plate(session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.get_all()

@router.put("/{meal_plate_id}")
def update_meal_plate(meal_plate_id: int, data: MealPlateUpdate, session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.update(meal_plate_id, data)

@router.delete("/{meal_plate_id}")
def delete_meal_plate(meal_plate_id: int, session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    resource.delete(meal_plate_id)
    return {"msg": "MealPlate eliminada exitosamente"}