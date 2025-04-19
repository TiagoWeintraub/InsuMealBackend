from fastapi import APIRouter, HTTPException, UploadFile, File
from sqlmodel import Session, select
from database import get_session
from backend.resources.gemini_resource import GeminiResource
from models.user import User
from backend.models.food_history import FoodHistory
from backend.models.meal_plate import MealPlate
from models.ingredient import Ingredient
from backend.models.clinical_data import ClinicalData
from backend.models.meal_plate_ingredient import MealPlateIngredient


router = APIRouter()
vision_resource = GeminiResource()

@router.post("/gemini/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = vision_resource.analyze_image(image_bytes)
    return {"result": result}


# Crear usuario
@router.post("/users/")
async def create_user(user: User):
    with get_session() as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

# Eliminar usuario
@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(user)
        session.commit()
        return {"message": "User deleted successfully"}

# Obtener todos los usuarios
@router.get("/users/")
async def get_users():
    with get_session() as session:
        users = session.exec(select(User)).all()
        return [user.to_json() for user in users]


# Obtener usuario por ID
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.to_json()


# Actualizar usuario
@router.put("/users/{user_id}")
async def update_user(user_id: int, user_data: User):
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.name = user_data.name
        user.email = user_data.email
        user.password = user_data.password
        session.commit()
        session.refresh(user)
        return user.to_json()


# Cambiar contraseña
@router.put("/users/{user_id}/change-password")
async def change_password(user_id: int, password_data: dict):
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.plain_password = password_data.get("new_password")
        session.commit()
        session.refresh(user)
        return {"message": "Password changed successfully"}



