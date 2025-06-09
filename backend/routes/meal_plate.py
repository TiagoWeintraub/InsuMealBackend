from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlmodel import Session
from database import get_session
from resources.meal_plate_resource import MealPlateResource
from schemas.meal_plate_schema import MealPlateUpdate, MealPlateCreate
from auth.dependencies import get_current_user

router = APIRouter(prefix="/meal_plate", tags=["meal_plate"])

# @router.post("/")
# async def create_meal_plate



@router.get("/")
async def read_meal_plate(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.get_all()

@router.get("/image/{meal_plate_id}")
async def get_meal_plate_image(meal_plate_id: int, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.get_image(meal_plate_id)

@router.put("/{meal_plate_id}")
async def update_meal_plate(meal_plate_id: int, data: MealPlateUpdate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.update(meal_plate_id, data)

# Borrar todos los Meal Plates de un usuario
@router.delete("/all")
async def delete_all_meal_plates(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    resource.delete_all()
    session.commit()

    return {"msg": "Todos los Meal Plates eliminados exitosamente"}


@router.delete("/{meal_plate_id}")
async def delete_meal_plate(meal_plate_id: int, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    resource.delete(meal_plate_id)
    return {"msg": "MealPlate eliminada exitosamente"}

