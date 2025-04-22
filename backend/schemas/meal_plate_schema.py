from pydantic import BaseModel
from datetime import datetime

class MealPlateBase(BaseModel):
    title: str
    description: str

class MealPlateCreate(MealPlateBase):
    picture: bytes
    type: str
    food_history_id: int

class MealPlateUpdate(MealPlateBase):
    pass