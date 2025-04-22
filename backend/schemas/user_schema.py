from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    name: str
    lastName: str
    email: EmailStr
    password: str



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
