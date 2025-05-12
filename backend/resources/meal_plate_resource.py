from sqlmodel import Session, select
from fastapi import HTTPException
from fastapi.responses import Response
from models.meal_plate import MealPlate
from schemas.meal_plate_schema import MealPlateRead
from schemas.meal_plate_schema import MealPlateUpdate
from resources.ingredient_resource import IngredientResource

class MealPlateResource:
    def __init__(self, session: Session):
        self.session = session

    def create(self, *, picture: bytes, mime_type: str, type: str, food_history_id: int, totalCarbs: float = None, glycemia: float = 100, dosis: float = None) -> MealPlate:
        meal_plate = MealPlate(
            picture=picture,
            picture_mime_type=mime_type,
            type=type,
            food_history_id=food_history_id,
            totalCarbs=totalCarbs,
            glycemia=glycemia,
            dosis=dosis
        )
        self.session.add(meal_plate)
        self.session.commit()
        self.session.refresh(meal_plate)
        return meal_plate


    def get_by_id(self, id: int):
        plate = self.session.exec(select(MealPlate).where(MealPlate.id == id)).first()
        if not plate:
            raise HTTPException(status_code=404, detail="MealPlate no encontrado")
        return plate 


    def get_last_by_user_id(self, user_id: int):
        # Primero, obtener los food_history_ids del usuario
        from models.food_history import FoodHistory
        
        food_histories = self.session.exec(
            select(FoodHistory).where(FoodHistory.user_id == user_id)
        ).all()
        
        if not food_histories:
            raise HTTPException(status_code=404, detail="Historial de comidas no encontrado para este usuario")
        
        food_history_ids = [fh.id for fh in food_histories]
        
        # Buscar el meal_plate más reciente para ese usuario
        plate = self.session.exec(
            select(MealPlate)
            .where(MealPlate.food_history_id.in_(food_history_ids))
            .order_by(MealPlate.id.desc())  # Ordenar por ID descendente asumiendo que IDs más altos son más recientes
        ).first()
        
        if not plate:
            raise HTTPException(status_code=404, detail="MealPlate no encontrado")
        
        return plate
    

    def get_all(self):
        meal_plates = self.session.exec(select(MealPlate)).all()
        result = []
        for plate in meal_plates:
            result.append(
                MealPlateRead(
                    id=plate.id,
                    type=plate.type,
                    totalCarbs=plate.totalCarbs,
                    glycemia=plate.glycemia,
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

    def calculate_total_carbs(self, meal_plate_id: int):
        total_carbs = 0.0
        # Encuentra todos los ingredientes asociados al MealPlate
        ingredient_resource = IngredientResource(self.session)
        meal_plate_data = ingredient_resource.read_ingredients_by_meal_plate(meal_plate_id)
        
        # Iterar sobre la lista de ingredientes en el diccionario devuelto
        for ingredient in meal_plate_data["ingredients"]:
            # Sumar los carbohidratos de cada ingrediente
            total_carbs += ingredient["carbs"]
    
        total_carbs = round(total_carbs, 2)
        # Actualiza el total de carbohidratos en el MealPlate
        self.update(meal_plate_id, MealPlateUpdate(totalCarbs=total_carbs))
    
        return total_carbs

    # Metodo para calcular el total de carbohidratos de un solo ingrediente
    def calculate_ingredient_total_carbs(self, ingredient_id: int, grams: float):
        ingredient_resource = IngredientResource(self.session)
        ingredient = ingredient_resource.get_by_id(ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
        carbs = round((ingredient.carbsPerHundredGrams * grams) / 100, 2)
        return carbs