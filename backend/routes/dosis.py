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
from resources.nutritionix_resource import NutritionixResource
from resources.dosis_resource import DosisResource
from schemas.meal_plate_schema import Glycemia

router = APIRouter(
    prefix="/dosis"
)

@router.post("/calculate/{meal_plate_id}")
async def calculate_dosis( data: Glycemia, current_user: User = Depends(get_current_user), session: Session = Depends(get_session), meal_plate_id: int = None):
    try:
        # Primero se calula el total de carbohidratos del plato de comida
        meal_plate_resource = MealPlateResource(session)
        total_carbs = meal_plate_resource.calculate_total_carbs(meal_plate_id)

        # Luego se calcula la dosis de insulina
        dosis_resource = DosisResource(session, current_user)
        dosis = dosis_resource.calculate(current_user,data.glycemia, meal_plate_id)

        return {"message": "Dosis calculada correctamente", "dosis": dosis, "glycemia": data.glycemia}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Problemas al calcular la dosis: {str(e)}")