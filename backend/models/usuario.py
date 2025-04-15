# from sqlmodel import SQLModel, Field
# from typing import Optional

# class Usuario(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     dni: int
#     email: str
#     nombre: str
#     apellido: str
#     contrasena: str = Field(..., alias="contraseña")
#     telefono: int

#     @property
#     def plain_contrasena(self):
#         raise AttributeError('Contraseña no puede ser leída')

#     @plain_contrasena.setter
#     def plain_contrasena(self, contrasena: str):
#         # self.contrasena = generate_password_hash(contrasena)
#         pass

#     def validate_pass(self, contrasena: str) -> bool:
#         # return check_password_hash(self.contrasena, contrasena)
#         pass

#     def __repr__(self):
#         return f"<Usuario {self.nombre} {self.apellido} ({self.telefono}, {self.email})>"

#     def to_json(self):
#         return {
#             'id': self.id,
#             'dni': self.dni,
#             'nombre': self.nombre,
#             'apellido': self.apellido,
#             'telefono': self.telefono,
#             'email': self.email,
#             'contraseña': self.contrasena
#         }

#     @staticmethod
#     def from_json(usuarios_json):
#         return Usuario(
#             id=usuarios_json.get('id'),
#             dni=usuarios_json.get('dni'),
#             nombre=usuarios_json.get('nombre'),
#             apellido=usuarios_json.get('apellido'),
#             contrasena=usuarios_json.get('contraseña'),
#             telefono=usuarios_json.get('telefono'),
#             email=usuarios_json.get('email')
#         )