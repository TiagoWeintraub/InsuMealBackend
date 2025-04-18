from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    name: str
    lastName: str
    password: str = Field(..., alias="password")

    @property
    def plain_password(self):
        raise AttributeError('Contraseña no puede ser leída')

    @plain_password.setter
    def plain_password(self, password: str):
        # self.password = generate_password_hash(password)
        pass

    def validate_pass(self, password: str) -> bool:
        # return check_password_hash(self.password, password)
        pass

    def __repr__(self):
        return f"<User {self.name} {self.lastName}, {self.email})>"

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'lastName': self.lastName,
            'email': self.email,
            'password': self.password
        }

    @staticmethod
    def from_json(users_json):
        return User(
            id=users_json.get('id'),
            dni=users_json.get('dni'),
            name=users_json.get('name'),
            lastName=users_json.get('lastName'),
            password=users_json.get('password'),
            telefono=users_json.get('telefono'),
            email=users_json.get('email')
        )