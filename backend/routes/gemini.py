from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from resources.gemini_resource import GeminiResource
from auth.dependencies import get_current_user
from models.user import User

router = APIRouter()
vision_resource = GeminiResource()

@router.post("/gemini/analyze-image")
async def analyze_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    image_bytes = await file.read()
    result = vision_resource.analyze_image(image_bytes)
    return {"result": result}