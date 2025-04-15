# from sqlmodel import SQLModel, Field
# from typing import Optional

# class Historial(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     usuario_id: int = Field(foreign_key="usuario.id")
#     imagen: str

#     def to_json(self):
#         return {
#             'id': self.id,
#             'usuario_id': self.usuario_id,
#             'imagen': self.imagen
#         }

#     @staticmethod
#     def from_json(historial_json):
#         return Historial(
#             id=historial_json.get('id'),
#             usuario_id=historial_json.get('usuario_id'),
#             imagen=historial_json.get('imagen')
#         )