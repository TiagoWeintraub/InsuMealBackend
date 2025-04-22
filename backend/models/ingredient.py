from typing import TYPE_CHECKING, List, Optional
from sqlmodel import SQLModel, Field, Relationship
from .meal_plate_ingredient import MealPlateIngredient

if TYPE_CHECKING:
    from .meal_plate import MealPlate

class Ingredient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    carbsPerHundredgrams: float

    # Relación bidireccional Muchos-a-Muchos con MealPlate
    meal_plates: List["MealPlate"] = Relationship(
        back_populates="ingredients",
        link_model=MealPlateIngredient 
    )

    def __repr__(self):
        return f"<Ingredient id={self.id}, name='{self.name}'>"