from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from backend.models.user import User


class ClinicalData(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    ratio: float
    sensitivity: float

    user: "User" = Relationship(back_populates="clinical_data")

    # def to_json(self):
    #     return {
    #         "id": self.id,
    #         "ratio": self.ratio,
    #         "sensitivity": self.sensitivity,
    #     }

    # @staticmethod
    # def from_json(data: dict) -> "ClinicalData":
    #     return ClinicalData(
    #         id=data.get("id"),
    #         ratio=data.get("ratio"),
    #         sensitivity=data.get("sensitivity"),
    #     )