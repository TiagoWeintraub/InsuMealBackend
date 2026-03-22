from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    name: str
    lastName: str
    email: EmailStr
    password: str
    # El valor de la ratio default es 15.0
    ratio: Optional[float] = 15.0
    sensitivity: Optional[float] = 50.0
    glycemiaTarget: Optional[int] = 100



class UserRead(BaseModel):
    id: int
    name: str
    lastName: str
    email: EmailStr

    model_config = {
        "from_attributes": True
    }

class UserDelete(BaseModel):
    id: int

    model_config = {
        "from_attributes": True
    }


class UserUpdate(BaseModel):
    name: str
    lastName: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class LoginInput(BaseModel):
    email: EmailStr
    password: str


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None  # "admin" | "user"


class AdminUserRead(BaseModel):
    id: int
    name: str
    lastName: str
    email: EmailStr
    role: str


class UsageBreakdownItem(BaseModel):
    provider: str
    model_name: str
    requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class UserUsageSummary(BaseModel):
    user_id: int
    total_requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    breakdown: list[UsageBreakdownItem]
