from sqlmodel import Session, select
from fastapi import HTTPException
from models.ingredient import Ingredient
from schemas.ingredient_schema import IngredientCreate, IngredientUpdate

class IngredientResource:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: IngredientCreate) -> Ingredient:
        ingredient = Ingredient(**data.model_dump()())
        self.session.add(ingredient)
        self.session.commit()
        self.session.refresh(ingredient)
        return ingredient

    def get_all(self):
        return self.session.exec(select(Ingredient)).all()

    def update(self, ingredient_id: int, data: IngredientUpdate) -> Ingredient:
        ingredient = self.session.get(Ingredient, ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient no encontrado")
        for key, value in data.model_dump()().items():
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