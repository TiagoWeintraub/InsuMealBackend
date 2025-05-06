from pydantic import BaseModel

class IngredientBase(BaseModel):
    name: str
    carbsPerHundredGrams: float
    meal_plate_id: int

class IngredientCreate(IngredientBase):
    name: str
    carbsPerHundredGrams: float
    meal_plate_id: int

class IngredientUpdate(IngredientBase):
    carbsPerHundredGrams: float