from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from backend.models.meal_plate import MealPlate 
from backend.models.meal_plate_ingredient import MealPlateIngredient


class Ingredient(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    carbsPerHundredgrams: float

    mealplates: List["MealPlate"] = Relationship(
        back_populates="ingredients", link_model=MealPlateIngredient
    )

    # def to_json(self):
    #     return {
    #         "id": self.id,
    #         "name": self.name,
    #         "carbsPerHundredgrams": self.carbsPerHundredgrams,
    #     }

    # @staticmethod
    # def from_json(data: dict) -> "Ingredient":
    #     return Ingredient(
    #         id=data.get("id"),
    #         name=data.get("name"),
    #         carbsPerHundredgrams=data.get("carbsPerHundredgrams"),
    #     )