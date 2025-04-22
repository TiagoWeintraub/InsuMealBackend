from sqlmodel import Session, select
from fastapi import HTTPException
from models.food_history import FoodHistory
from schemas.food_history_schema import FoodHistoryCreate, FoodHistoryUpdate

class FoodHistoryResource:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: FoodHistoryCreate) -> FoodHistory:
        food_history = FoodHistory(**data.model_dump()())
        self.session.add(food_history)
        self.session.commit()
        self.session.refresh(food_history)
        return food_history

    def get_all(self):
        return self.session.exec(select(FoodHistory)).all()

    def update(self, food_history_id: int, data: FoodHistoryUpdate) -> FoodHistory:
        food_history = self.session.get(FoodHistory, food_history_id)
        if not food_history:
            raise HTTPException(status_code=404, detail="FoodHistory no encontrado")
        for key, value in data.model_dump()().items():
            setattr(food_history, key, value)
        self.session.add(food_history)
        self.session.commit()
        self.session.refresh(food_history)
        return food_history

    def delete(self, food_history_id: int):
        food_history = self.session.get(FoodHistory, food_history_id)
        if not food_history:
            raise HTTPException(status_code=404, detail="FoodHistory no encontrado")
        self.session.delete(food_history)
        self.session.commit()