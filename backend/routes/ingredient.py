from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from resources.ingredient_resource import IngredientResource
from schemas.ingredient_schema import IngredientCreate, IngredientUpdate
from auth.dependencies import get_current_user

router = APIRouter(prefix="/ingredient", tags=["ingredient"])

@router.post("/")
async def create_ingredient(data: IngredientCreate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    return resource.create(data)

@router.get("/all") # Todos los ingredientes
async def read_ingredients(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    return resource.get_all()

@router.get("/{ingredient_name}") # Ingrediente por nombre
async def read_ingredient_by_name(ingredient_name: str, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    ingredient = resource.get_all()
    for i in ingredient:
        if i.name == ingredient_name:
            return i
    return {"msg": "No se encontró el ingrediente"} 

@router.get("/meal_plate/{meal_plate_id}") # Ingredientes por MealPlate
async def get_meal_plate_with_ingredients(
    meal_plate_id: int,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session)
):
    resource = IngredientResource(session)
    return resource.read_ingredients_by_meal_plate(meal_plate_id)

@router.put("/{ingredient_id}")
async def update_ingredient(ingredient_id: int, data: IngredientUpdate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    return resource.update(ingredient_id, data)

@router.delete("/all")
async def delete_all_ingredients(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    return resource.delete_all_ingredients()

@router.delete("/{ingredient_id}")
async def delete_ingredient(ingredient_id: int, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    resource.delete(ingredient_id)
    return {"msg": "Ingredient eliminada exitosamente"}