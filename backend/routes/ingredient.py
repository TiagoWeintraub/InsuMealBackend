from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from resources.ingredient_resource import IngredientResource
from schemas.ingredient_schema import IngredientCreate, IngredientUpdate
from auth.dependencies import get_current_user  # Nuevo import

router = APIRouter(prefix="/ingredient", tags=["ingredient"])

@router.post("/")
def create_ingredient(data: IngredientCreate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    return resource.create(data)

@router.get("/")
def read_ingredients(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    return resource.get_all()

@router.put("/{ingredient_id}")
def update_ingredient(ingredient_id: int, data: IngredientUpdate, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    return resource.update(ingredient_id, data)

@router.delete("/{ingredient_id}")
def delete_ingredient(ingredient_id: int, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    resource = IngredientResource(session)
    resource.delete(ingredient_id)
    return {"msg": "Ingredient eliminada exitosamente"}