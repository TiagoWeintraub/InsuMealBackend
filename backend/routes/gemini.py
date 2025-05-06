from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlmodel import Session
from resources.gemini_resource import GeminiResource
from auth.dependencies import get_current_user
from models.user import User
from database import get_session
from resources.usda_resource import UsdaResource
from resources.nutritionix_resource import NutritionixResource
router = APIRouter()

@router.post("/gemini/analyze-image")
async def analyze_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user),session: Session = Depends(get_session)):
    image_bytes = await file.read()
    vision_resource = GeminiResource(session)
    result = vision_resource.analyze_image(image_bytes, current_user)
    return {"result": result}

@router.get("/gemini/usda")
async def get_usda_data(session: Session = Depends(get_session), current_user: User = Depends(get_current_user), food_dic: dict = {}):
    usda_resource = UsdaResource(session, current_user)
    food_data = usda_resource.orquest(food_dic)
    return {"food_data": food_data}



