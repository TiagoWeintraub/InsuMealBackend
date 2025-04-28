from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlmodel import Session
from resources.gemini_resource import GeminiResource
from auth.dependencies import get_current_user
from models.user import User
from database import get_session

router = APIRouter()

@router.post("/gemini/analyze-image")
async def analyze_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user),session: Session = Depends(get_session)):
    image_bytes = await file.read()
    vision_resource = GeminiResource(session)
    result = vision_resource.analyze_image(image_bytes, current_user)
    return {"result": result}

