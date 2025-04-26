from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MealPlateBase(BaseModel):
    picture: bytes
    type: str
    food_history_id: int

class MealPlateCreate(MealPlateBase):
    picture: bytes
    type: str
    food_history_id: int


class MealPlateRead(BaseModel):
    id: int
    type: str
    totalCarbs: Optional[float]
    dosis: Optional[float]
    image_url: str

    class Config:
        from_attributes = True


class MealPlateUpdate(MealPlateBase):
    type: str
