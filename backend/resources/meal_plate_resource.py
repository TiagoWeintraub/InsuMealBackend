from sqlmodel import Session, select
from fastapi import HTTPException
from fastapi.responses import Response
from models.meal_plate import MealPlate
from schemas.meal_plate_schema import MealPlateRead

class MealPlateResource:
    def __init__(self, session: Session):
        self.session = session

    def create(self, *, picture: bytes, mime_type: str, type: str, food_history_id: int, totalCarbs: float = None, dosis: float = None) -> MealPlate:
        meal_plate = MealPlate(
            picture=picture,
            picture_mime_type=mime_type,
            type=type,
            food_history_id=food_history_id,
            totalCarbs=totalCarbs,
            dosis=dosis
        )
        self.session.add(meal_plate)
        self.session.commit()
        self.session.refresh(meal_plate)
        return meal_plate.id

    def get_all(self):
        meal_plates = self.session.exec(select(MealPlate)).all()
        result = []
        for plate in meal_plates:
            result.append(
                MealPlateRead(
                    id=plate.id,
                    type=plate.type,
                    totalCarbs=plate.totalCarbs,
                    dosis=plate.dosis,
                    image_url=f"/meal_plate/image/{plate.id}"
                )
            )
        return result
    
    def get_image(self, meal_plate_id: int):
        meal_plate = self.session.get(MealPlate, meal_plate_id)
        if not meal_plate or not meal_plate.picture:
            raise HTTPException(status_code=404, detail="MealPlate no encontrado")
        return Response(content=meal_plate.picture, media_type=meal_plate.picture_mime_type)

    def update(self, meal_plate_id: int, data) -> MealPlate:
        meal_plate = self.session.get(MealPlate, meal_plate_id)
        if not meal_plate:
            raise HTTPException(status_code=404, detail="MealPlate no encontrado")
        for key, value in data.model_dump(exclude_unset=True).items():
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

    def delete_all(self):
        meal_plates = self.session.exec(select(MealPlate)).all()
        for plate in meal_plates:
            self.session.delete(plate)
        self.session.commit()
        return {"msg": "Todos los Meal Plates eliminados exitosamente"}