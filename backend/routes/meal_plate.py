from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlmodel import Session
from database import get_session
from resources.meal_plate_resource import MealPlateResource
from schemas.meal_plate_schema import MealPlateUpdate
from auth.dependencies import get_current_user

router = APIRouter(prefix="/meal_plate", tags=["meal_plate"])

@router.post("/")
async def create_meal_plate(
    picture: UploadFile = File(...),
    type: str = Form(...),
    totalCarbs: float = Form(None),
    dosis: float = Form(None),
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session)
):
    resource = MealPlateResource(session)
    picture_bytes = await picture.read()
    return resource.create(picture=picture_bytes, type=type, totalCarbs=totalCarbs, dosis=dosis)

@router.get("/")
def read_meal_plate(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.get_all()

@router.get("/image/{meal_plate_id}")
def get_meal_plate_image(meal_plate_id: int, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.get_image(meal_plate_id)

@router.put("/{meal_plate_id}")
def update_meal_plate(meal_plate_id: int, data: MealPlateUpdate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    return resource.update(meal_plate_id, data)

@router.delete("/{meal_plate_id}")
def delete_meal_plate(meal_plate_id: int, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = MealPlateResource(session)
    resource.delete(meal_plate_id)
    return {"msg": "MealPlate eliminada exitosamente"}
