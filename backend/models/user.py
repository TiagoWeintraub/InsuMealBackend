from sqlmodel import SQLModel, Field, Relationship
from typing import List
from backend.models.clinical_data import ClinicalData
from backend.models.food_history import FoodHistory
from werkzeug.security import generate_password_hash, check_password_hash

class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    lastName: str
    email: str
    password: str
    idClinicalData: int = Field(foreign_key="clinicaldata.id", nullable=False, unique=True)

    clinical_data: ClinicalData = Relationship(back_populates="user")
    food_history: List["FoodHistory"] = Relationship(back_populates="user")

    @property
    def plain_password(self):
        # No se permite la lectura de la contraseña.
        raise AttributeError("La contraseña no puede ser leída directamente")

    @plain_password.setter
    def plain_password(self, password: str):
        # Se guarda el hash generado.
        self.password = generate_password_hash(password)

    def validate_pass(self, password: str) -> bool:
        # Comprueba si el password coincide con el hash almacenado.
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User {self.name} {self.lastName}, {self.email}>"

    # def to_json(self):
    #     return {
    #         "id": self.id,
    #         "name": self.name,
    #         "lastName": self.lastName,
    #         "email": self.email
    #         # No se expone la contraseña
    #     }

    # @staticmethod
    # def from_json(data: dict) -> "User":
    #     user = User(
    #         id=data.get("id"),
    #         name=data.get("name"),
    #         lastName=data.get("lastName"),
    #         email=data.get("email"),
    #         idClinicalData=data.get("idClinicalData")
    #     )
    #     if data.get("password"):
    #         user.plain_password = data.get("password")
    #     return user