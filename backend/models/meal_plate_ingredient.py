from typing import Optional, List
from sqlmodel import SQLModel, Field


class MealPlateIngredient(SQLModel, table=True):
    mealplate_id: int = Field(foreign_key="mealplate.id", primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id", primary_key=True)
