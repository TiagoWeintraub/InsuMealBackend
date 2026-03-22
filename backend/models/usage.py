from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, ForeignKey, Integer

if TYPE_CHECKING:
    from .user import User


class Usage(SQLModel, table=True):
    __tablename__ = "usage"

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(default="google", index=True)
    model_name: str = Field(default="gemini-2.5-flash-lite", index=True)
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    user: Optional["User"] = Relationship(back_populates="usages")

    def __repr__(self):
        return f"<Usage id={self.id}, user_id={self.user_id}, total_tokens={self.total_tokens}>"
