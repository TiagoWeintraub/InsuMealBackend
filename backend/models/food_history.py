from typing import TYPE_CHECKING, Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from sqlalchemy import Column, ForeignKey, Integer, DateTime, func

if TYPE_CHECKING:
    from .meal_plate import MealPlate
    from .user import User

class FoodHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Campo de fecha con valor por defecto generado por la BD
    date: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
            index=True 
        )
    )

    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("user.id", ondelete="CASCADE"), # FK con cascade
            nullable=False,
            unique=True 
        )
    )

    # Relación bidireccional Uno-a-Uno con User
    user: Optional["User"] = Relationship(
        back_populates="food_history",
        sa_relationship_kwargs={'uselist': False} 
    )
    # Relación bidireccional Uno-a-Muchos con MealPlate
    meal_plates: List["MealPlate"] = Relationship(back_populates="food_history")

    def __repr__(self):
        return f"<FoodHistory id={self.id}, user_id={self.user_id}>"