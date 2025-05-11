from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import Dict, Any
from pydantic import BaseModel

from database import get_session
from models.user import User
from auth.dependencies import get_current_user
from resources.nutritionix_resource import NutritionixResource
from resources.meal_plate_resource import MealPlateResource
from resources.ingredient_resource import IngredientResource
from models.meal_plate import MealPlate


router = APIRouter(
    prefix="/nutrition"
)

@router.post("/add/food/{meal_plate_id}")
async def process_foods(meal_plate_id: int, food_dic: dict = {},current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
        nutritionix_resource = NutritionixResource(session, current_user)
        meal_plate = session.get(MealPlate, meal_plate_id)
        if not meal_plate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MealPlate no encontrado")
        
        result = nutritionix_resource.orquest(food_dic, meal_plate)

        return result.id

