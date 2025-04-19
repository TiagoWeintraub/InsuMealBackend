from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from backend.models.meal_plate import MealPlate
from backend.models.user import User

class FoodHistory(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    date: datetime
    idUser: int = Field(foreign_key="user.id", nullable=False)
    idMealPlate: int = Field(foreign_key="mealplate.id", nullable=False)

    user: User = Relationship(back_populates="food_history")
    mealplate: MealPlate = Relationship(back_populates="food_histories")


    # def to_json(self):
    #     return {
    #         "id": self.id,
    #         "date": self.date.isoformat(),
    #         "idUser": self.idUser,
    #         "idMealPlate": self.idMealPlate,
    #     }

    # @staticmethod
    # def from_json(data: dict) -> "FoodHistory":
    #     return FoodHistory(
    #         id=data.get("id"),
    #         date=datetime.fromisoformat(data.get("date")),
    #         idUser=data.get("idUser"),
    #         idMealPlate=data.get("idMealPlate"),
    #     )