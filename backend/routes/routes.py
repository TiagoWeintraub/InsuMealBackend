from fastapi import APIRouter, HTTPException, UploadFile, File
from sqlmodel import Session, select
from models.usuario import Usuario
# from models.historial import Historial
from database import get_session
from resources.geminiResource import GeminiResource

router = APIRouter()
vision_resource = GeminiResource()

@router.post("/gemini/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = vision_resource.analyze_image(image_bytes)
    return {"result": result}


@router.post("/usuarios/")
async def create_user(usuario: Usuario):
    with get_session() as session:
        session.add(usuario)
        session.commit()
        session.refresh(usuario)
        return usuario


# @router.get("/historial/{usuario_id}")
# async def get_historial(usuario_id: int):
#     with get_session() as session:
#         statement = select(Historial).where(Historial.usuario_id == usuario_id)
#         results = session.exec(statement).all()
#         return results