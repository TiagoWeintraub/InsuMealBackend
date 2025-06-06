from sqlmodel import Session, select
from fastapi import HTTPException
from models.meal_plate_ingredient import MealPlateIngredient
from schemas.meal_plate_ingredient_schema import MealPlateIngredientUpdate
from schemas.meal_plate_ingredient_schema import MealPlateIngredientRead
from models.user import User

class MealPlateIngredientResource:
    def __init__(self, session: Session, current_user: User = None):
        self.session = session
        self.current_user = current_user

    def update(self, meal_plate_id: int, ingredient_id: int, data: MealPlateIngredientUpdate) -> MealPlateIngredient:
        meal_plate_ingredient = self.session.get(MealPlateIngredient, (meal_plate_id, ingredient_id))
        if not meal_plate_ingredient:
            raise HTTPException(status_code=404, detail="MealPlateIngredient no encontrado")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(meal_plate_ingredient, field, value)

        self.session.add(meal_plate_ingredient)
        self.session.commit()
        self.session.refresh(meal_plate_ingredient)

        return meal_plate_ingredient

    def get_all(self):
        meal_plate_ingredients = self.session.exec(select(MealPlateIngredient)).all()
        if not meal_plate_ingredients:
            raise HTTPException(status_code=404, detail="No se encontraron MealPlateIngredients")
        return [
            MealPlateIngredientRead(
                meal_plate_id=ingredient.meal_plate_id,
                ingredient_id=ingredient.ingredient_id,
                grams=ingredient.grams,
                carbs=ingredient.carbs
            ) for ingredient in meal_plate_ingredients
        ]

    def get_one(self, meal_plate_id: int, ingredient_id: int) -> MealPlateIngredientRead:
        meal_plate_ingredient = self.session.get(MealPlateIngredient, (meal_plate_id, ingredient_id))
        if not meal_plate_ingredient:
            raise HTTPException(status_code=404, detail="MealPlateIngredient no encontrado")
        return MealPlateIngredientRead(
            meal_plate_id=meal_plate_ingredient.meal_plate_id,
            ingredient_id=meal_plate_ingredient.ingredient_id,
            grams=meal_plate_ingredient.grams,
            carbs=meal_plate_ingredient.carbs
        )
    
    def add_ingredient_to_meal_plate(self, meal_plate_id: int, ingredient_id: int, grams: float) -> MealPlateIngredient:
        meal_plate_ingredient = MealPlateIngredient(meal_plate_id=meal_plate_id, ingredient_id=ingredient_id, grams=grams)
        self.session.add(meal_plate_ingredient)
        self.session.commit()
        self.session.refresh(meal_plate_ingredient)
        return meal_plate_ingredient