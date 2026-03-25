from typing import TYPE_CHECKING, List, Optional
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .user import User


class Role(SQLModel, table=True):
    __tablename__ = "role"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)

    users: List["User"] = Relationship(back_populates="role")

    def __repr__(self):
        return f"<Role id={self.id}, name='{self.name}'>"
