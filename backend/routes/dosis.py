from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import Dict, Any
from pydantic import BaseModel

from database import get_session
from models.user import User
from auth.dependencies import get_current_user
from resources.meal_plate_resource import MealPlateResource
from resources.ingredient_resource import IngredientResource
from models.meal_plate import MealPlate
from resources.dosis_resource import DosisResource


router = APIRouter(
    prefix="/dosis"
)

@router.post("/calculate")
async def process_foods(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
        dosis_resource = DosisResource(session, current_user)
        dosis_resource.calculate(current_user=current_user)


        return 

