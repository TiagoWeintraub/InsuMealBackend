from typing import TYPE_CHECKING, Optional, List
from sqlmodel import SQLModel, Field, Relationship
# Importar la clase real de la tabla de enlace
from .meal_plate_ingredient import MealPlateIngredient
# Importaciones SQLAlchemy para definición explícita de columnas
from sqlalchemy import Column, ForeignKey, Integer, String, LargeBinary, Float

if TYPE_CHECKING:
    from .ingredient import Ingredient
    from .food_history import FoodHistory

class MealPlate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    picture: bytes = Field(sa_column=Column(LargeBinary, nullable=False)) 
    type: str = Field(...)
    totalCarbs: Optional[float] = Field(default=None)
    dosis: Optional[float] = Field(default=None)

    food_history_id: Optional[int] = Field(
        default=None, 
        sa_column=Column( 
            Integer,
            ForeignKey("foodhistory.id", ondelete="CASCADE"), # FK con cascade
            nullable=True # Permitir MealPlates sin FoodHistory 
        )
    )

    # Relación bidireccional Muchos-a-Muchos con Ingredient
    ingredients: List["Ingredient"] = Relationship(
        back_populates="meal_plates",
        link_model=MealPlateIngredient
    )

    # Relación bidireccional Muchos-a-Uno con FoodHistory
    food_history: Optional["FoodHistory"] = Relationship(back_populates="meal_plates")

    def __repr__(self):
        return f"<MealPlate id={self.id}, type='{self.type}', food_history_id={self.food_history_id}>"