from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlmodel import Session
from database import get_session
from resources.meal_plate_resource import MealPlateResource
from schemas.meal_plate_schema import MealPlateUpdate, MealPlateCreate
from auth.dependencies import get_current_user

router = APIRouter(prefix="/meal_plate", tags=["meal_plate"])

@router.post("/")
async def create_meal_plate(
    form_data: MealPlateCreate = Depends(), 
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session)
):
    picture_bytes = await form_data.picture.read()

    data = {
        "picture": picture_bytes,
        "picture_mime_type": form_data.picture.content_type,
        "type": form_data.type,
        "food_history_id": form_data.food_history_id,
        "totalCarbs": form_data.totalCarbs,
        "dosis": form_data.dosis,
    }

    resource = MealPlateResource(session)
    return resource.create_from_dict(data)


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
