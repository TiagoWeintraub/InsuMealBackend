from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from models.ingredient import Ingredient
from schemas.ingredient_schema import IngredientCreate, IngredientUpdate
from models.meal_plate import MealPlate


class IngredientResource:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: IngredientCreate) -> Ingredient:
        # Verificar si el ingrediente ya existe basado en el nombre
        existing = self.session.exec(
            select(Ingredient).where(Ingredient.name == data.name)
        ).first()
        if existing:
            # Se verifica si el ingrediente ya está asociado al MealPlate
            meal_plate = self.session.get(MealPlate, data.meal_plate_id)
            if not meal_plate: # Si no existe el MealPlate lanza una excepción
                raise HTTPException(status_code=404, detail="MealPlate no encontrado")
            if existing not in meal_plate.ingredients: # Si no está asociado, se agrega
                meal_plate.ingredients.append(existing)
                self.session.add(meal_plate)
                self.session.commit()
            return existing
    
        # Si no existe, se crea el ingrediente y se establece la relación
        ingredient = Ingredient(**data.model_dump())
        self.session.add(ingredient)
        self.session.commit()
        self.session.refresh(ingredient)
    
        meal_plate = self.session.get(MealPlate, data.meal_plate_id)
        if not meal_plate:
            raise HTTPException(status_code=404, detail="MealPlate no encontrado")
        meal_plate.ingredients.append(ingredient)
        self.session.add(meal_plate)
        self.session.commit()
        
        return ingredient

    def get_all(self):
        return self.session.exec(select(Ingredient)).all()


    def read_ingredients_by_meal_plate(self, meal_plate_id: int) -> MealPlate:
        query = (
            select(MealPlate)
            .where(MealPlate.id == meal_plate_id)
            .options(selectinload(MealPlate.ingredients))
        )
        meal_plate = self.session.exec(query).first()
        if not meal_plate:
            raise HTTPException(status_code=404, detail="MealPlate no encontrado")
        # meal_plate.ingredients contiene la información completa de cada ingrediente
        return meal_plate

    def update(self, ingredient_id: int, data: IngredientUpdate) -> Ingredient:
        ingredient = self.session.get(Ingredient, ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient no encontrado")
        for key, value in data.model_dump().items():
            setattr(ingredient, key, value)
        self.session.add(ingredient)
        self.session.commit()
        self.session.refresh(ingredient)
        return ingredient

    def delete(self, ingredient_id: int):
        ingredient = self.session.get(Ingredient, ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient no encontrado")
        self.session.delete(ingredient)
        self.session.commit()
    
    def delete_all_ingredients(self):
        ingredients = self.session.exec(select(Ingredient)).all()
        for ingredient in ingredients:
            self.session.delete(ingredient)
        self.session.commit()
        return {"msg": "Todos los ingredientes eliminados exitosamente"}