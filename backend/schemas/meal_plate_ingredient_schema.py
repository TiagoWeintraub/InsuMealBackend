from pydantic import BaseModel
from typing import Optional


class MealPlateIngredientRead(BaseModel):
    meal_plate_id: int
    ingredient_id: int
    grams: Optional[float] = 0.0
    carbs: Optional[float] = 0.0

class MealPlateIngredientUpdate(BaseModel):
    grams: Optional[float] = None
    carbs: Optional[float] = None