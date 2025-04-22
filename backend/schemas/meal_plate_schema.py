from pydantic import BaseModel

class MealPlateBase(BaseModel):
    title: str
    description: str

class MealPlateCreate(MealPlateBase):
    pass

class MealPlateUpdate(MealPlateBase):
    pass