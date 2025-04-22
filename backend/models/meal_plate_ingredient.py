from typing import Optional
from sqlmodel import SQLModel, Field
# Importaciones SQLAlchemy para definición explícita de columnas
from sqlalchemy import Column, ForeignKey, Integer

class MealPlateIngredient(SQLModel, table=True):
    # Clave primaria/foránea a MealPlate con cascade
    meal_plate_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("mealplate.id", ondelete="CASCADE"), # FK con cascade
            primary_key=True, # PK en la BD
            nullable=False
        )
    )
    # Clave primaria/foránea a Ingredient con cascade
    ingredient_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("ingredient.id", ondelete="CASCADE"), # FK con cascade
            primary_key=True, # PK en la BD
            nullable=False
        )
    )

    # No necesita __repr__ usualmente