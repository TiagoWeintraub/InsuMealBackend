from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from schemas.meal_plate_ingredient_schema import MealPlateIngredientUpdate
from models.meal_plate_ingredient import MealPlateIngredient
from auth.dependencies import get_current_user  # Importar la dependencia para el usuario actual
from resources.meal_plate_ingredient_resource import MealPlateIngredientResource
from resources.meal_plate_resource import MealPlateResource

router = APIRouter(prefix="/meal_plate_ingredient", tags=["meal_plate_ingredient"], include_in_schema=True)

@router.put("/{meal_plate_id}/{ingredient_id}")
async def update_meal_plate_ingredient(
    meal_plate_id: int,
    ingredient_id: int,
    data: MealPlateIngredientUpdate,
    current_user=Depends(get_current_user),  # Validar el token de acceso
    session: Session = Depends(get_session)
):
    meal_plate_resource = MealPlateResource(session)
    resource = MealPlateIngredientResource(session)
    # Calcular el total de carbohidratos a partir de los ingredientes
    new_carbs = meal_plate_resource.calculate_ingredient_total_carbs(ingredient_id, data.grams)
    
    new_data = MealPlateIngredientUpdate(
        grams=data.grams,
        carbs=new_carbs
        )
    resource.update(meal_plate_id, ingredient_id, new_data)
    return {"message": "MealPlateIngredient actualizado exitosamente"}


@router.get("/")
async def get_all_meal_plate_ingredients(
    current_user=Depends(get_current_user),  # Validar el token de acceso
    session: Session = Depends(get_session)
):
    resource = MealPlateIngredientResource(session)
    meal_plate_ingredients = resource.get_all()
    return {"data": meal_plate_ingredients}


@router.get("/{meal_plate_id}/{ingredient_id}")
async def get_meal_plate_ingredient(
    meal_plate_id: int,
    ingredient_id: int,
    current_user=Depends(get_current_user),  # Validar el token de acceso
    session: Session = Depends(get_session)
):
    resource = MealPlateIngredientResource(session)
    meal_plate_ingredient = resource.get_one(meal_plate_id, ingredient_id)
    return {"data": meal_plate_ingredient}