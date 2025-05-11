from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey, Integer, Float

if TYPE_CHECKING:
    from .user import User

class ClinicalData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    ratio: float = Field(default=15.0) # Una unidad de insulina por 15 gramos de carbohidratos 
    sensitivity: float = Field(default=0.0) # Cuánto baja la glucosa por cada unidad de insulina
    glycemiaTarget: int = Field(default=100) # mg/dL


    user_id: Optional[int] = Field(
        default=None,
        sa_column=Column( # Definición de la columna en la BD
            Integer,
            ForeignKey("user.id", ondelete="CASCADE"), # FK con cascade
            unique=True, 
            nullable=False 
        )
    )

    # Relación bidireccional con User
    user: Optional["User"] = Relationship(
        back_populates="clinical_data",
        sa_relationship_kwargs={'uselist': False} 
    )

    def __repr__(self):
        return f"<ClinicalData id={self.id}, user_id={self.user_id}>"