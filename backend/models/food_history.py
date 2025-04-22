from typing import TYPE_CHECKING, Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey, Integer

if TYPE_CHECKING:
    from .meal_plate import MealPlate
    from .user import User

class FoodHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

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
    # Relación 1-a-Muchos con MealPlate - al eliminar FoodHistory se eliminan los MealPlate asociados
    meal_plates: List["MealPlate"] = Relationship(
        back_populates="food_history",
        sa_relationship_kwargs={"cascade": "all, delete"}
    )
    def __repr__(self):
        return f"<FoodHistory id={self.id}, user_id={self.user_id}>"