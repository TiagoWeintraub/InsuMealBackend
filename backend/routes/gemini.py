from fastapi import APIRouter, HTTPException, UploadFile, File
from resources.gemini_resource import GeminiResource


router = APIRouter()
vision_resource = GeminiResource()

@router.post("/gemini/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = vision_resource.analyze_image(image_bytes)
    return {"result": result}

