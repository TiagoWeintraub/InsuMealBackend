from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from backend.models.ingredient import Ingredient
from backend.models.meal_plate_ingredient import MealPlateIngredient
from backend.models.food_history import FoodHistory


class MealPlate(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    picture: bytes
    type: str
    totalCarbs: Optional[int] = None
    dosis: Optional[float] = None

    ingredients: List[Ingredient] = Relationship(
        back_populates="mealplates", link_model=MealPlateIngredient
    )
    food_histories: List["FoodHistory"] = Relationship(back_populates="mealplate")

    def __repr__(self):
        return f"MealPlate(id={self.id}, type={self.type}"
    
    # def to_json(self):
    #     return {
    #         "id": self.id,
    #         "picture": self.picture,
    #         "type": self.type,
    #         "totalCarbs": self.totalCarbs,
    #         "dosis": self.dosis,
    #     }
    
    # @staticmethod
    # def from_json(data: dict) -> "MealPlate":
    #     return MealPlate(
    #         id=data.get("id"),
    #         picture=data.get("picture"),
    #         type=data.get("type"),
    #         totalCarbs=data.get("totalCarbs"),
    #         dosis=data.get("dosis")
    #     )