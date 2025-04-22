from pydantic import BaseModel

class IngredientBase(BaseModel):
    name: str
    quantity: float

class IngredientCreate(IngredientBase):
    pass

class IngredientUpdate(IngredientBase):
    pass