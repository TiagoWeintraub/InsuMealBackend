from typing import TYPE_CHECKING, List, Optional
from sqlmodel import SQLModel, Field, Relationship
from werkzeug.security import generate_password_hash, check_password_hash

if TYPE_CHECKING:
    from .clinical_data import ClinicalData
    from .food_history import FoodHistory

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    lastName: str
    email: str = Field(unique=True, index=True) 
    password: str 

    # Relación bidireccional 1-a-1 con ClinicalData
    clinical_data: Optional["ClinicalData"] = Relationship(back_populates="user")

    # Relación bidireccional 1-a-Muchos con FoodHistory
    food_history: Optional["FoodHistory"] = Relationship(back_populates="user")

    @property
    def plain_password(self):
        raise AttributeError("La contraseña no puede ser leída directamente")

    @plain_password.setter
    def plain_password(self, password: str):
        self.password = generate_password_hash(password)

    def validate_pass(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User id={self.id}, email='{self.email}'>"