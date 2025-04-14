from fastapi import APIRouter, UploadFile, File
from resources.geminiService import GeminiService

router = APIRouter()
vision_service = GeminiService()

@router.post("/gemini/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = vision_service.analyze_image(image_bytes)
    return {"result": result}
