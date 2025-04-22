from sqlmodel import Session, select
from fastapi import HTTPException
from models.meal_plate import MealPlate
from schemas.meal_plate_schema import MealPlateCreate, MealPlateUpdate

class MealPlateResource:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: MealPlateCreate) -> MealPlate:
        meal_plate = MealPlate(**data.model_dump()())
        self.session.add(meal_plate)
        self.session.commit()
        self.session.refresh(meal_plate)
        return meal_plate

    def get_all(self):
        return self.session.exec(select(MealPlate)).all()

    def update(self, meal_plate_id: int, data: MealPlateUpdate) -> MealPlate:
        meal_plate = self.session.get(MealPlate, meal_plate_id)
        if not meal_plate:
            raise HTTPException(status_code=404, detail="MealPlate no encontrado")
        for key, value in data.model_dump()().items():
            setattr(meal_plate, key, value)
        self.session.add(meal_plate)
        self.session.commit()
        self.session.refresh(meal_plate)
        return meal_plate

    def delete(self, meal_plate_id: int):
        meal_plate = self.session.get(MealPlate, meal_plate_id)
        if not meal_plate:
            raise HTTPException(status_code=404, detail="MealPlate no encontrado")
        self.session.delete(meal_plate)
        self.session.commit()