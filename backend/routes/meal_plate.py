from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from resources.meal_plate_resource import MealPlateResource
from schemas.meal_plate_schema import MealPlateCreate, MealPlateUpdate
from auth.dependencies import get_current_user  # Nuevo import

router = APIRouter(prefix="/meal_plate", tags=["meal_plate"])


""" 
    Cuando se detecten los alimentos de la IA, en el recurso de gemini se debe llamar al meal plate resource
    para crear el meal plate, asociarlo al historial de comidas del usuario
    y por cada alimento detectado, crear un ingrediente y asociarlo al meal plate
"""

@router.post("/")
def create_meal_plate(data: MealPlateCreate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.create(data)

@router.get("/")
def read_meal_plate(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.get_all()

@router.put("/{meal_plate_id}")
def update_meal_plate(meal_plate_id: int, data: MealPlateUpdate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.update(meal_plate_id, data)

@router.delete("/{meal_plate_id}")
def delete_meal_plate(meal_plate_id: int, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    resource.delete(meal_plate_id)
    return {"msg": "MealPlate eliminada exitosamente"}