# schemas/meal_plate_schema.py
from pydantic import BaseModel
from fastapi import Form, UploadFile, File
from typing import Optional

class MealPlateCreate:
    def __init__(
        self,
        type: str = Form(...),
        food_history_id: int = Form(...),
        totalCarbs: Optional[float] = Form(None),
        glycemia: Optional[float] = Form(None),
        dosis: Optional[float] = Form(None),
        picture: UploadFile = File(...)
    ):
        self.type = type
        self.food_history_id = food_history_id
        self.totalCarbs = totalCarbs
        self.glycemia = glycemia
        self.dosis = dosis
        self.picture = picture

class MealPlateRead(BaseModel):
    date: str
    id: int
    type: str
    totalCarbs: Optional[float]
    glycemia: Optional[float]
    dosis: Optional[float]
    image_url: str

    class Config:
        from_attributes = True


class MealPlateUpdate(BaseModel):
    type: Optional[str] = None
    totalCarbs: Optional[float] = None
    glycemia: Optional[float] = None
    dosis: Optional[float] = None

    class Config:
        from_attributes = True

class Glycemia(BaseModel):
    glycemia: float