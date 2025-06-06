from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlmodel import Session
from resources.gemini_resource import GeminiResource
from auth.dependencies import get_current_user
from models.user import User
from database import get_session
from resources.usda_resource import UsdaResource
from resources.nutritionix_resource import NutritionixResource
from resources.ingredient_resource import IngredientResource
router = APIRouter()

@router.post("/gemini/analyze-image")
async def analyze_image(file: UploadFile = File(default=None), current_user: User = Depends(get_current_user),session: Session = Depends(get_session)):
    if not file:
        raise HTTPException(status_code=400, detail="No se ha subido ningún archivo. Asegúrate de incluir un archivo en el campo 'file'")
    try:
        image_bytes = await file.read()
        vision_resource = GeminiResource(session)
        meal_plate_id = vision_resource.analyze_image(image_bytes, current_user)
        
        resource = IngredientResource(session)
        return resource.read_ingredients_by_meal_plate(meal_plate_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {str(e)}")

@router.get("/gemini/usda")
async def get_usda_data(session: Session = Depends(get_session), current_user: User = Depends(get_current_user), food_dic: dict = {}):
    usda_resource = UsdaResource(session, current_user)
    food_data = usda_resource.orquest(food_dic)
    return {"food_data": food_data}



