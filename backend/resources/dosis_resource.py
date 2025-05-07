import os 
import io
from dotenv import load_dotenv
from sqlmodel import Session, select
from fastapi import HTTPException
from models.user import User
from resources.clinical_data_resource import ClinicalDataResource
from resources.meal_plate_resource import MealPlateResource
from schemas.meal_plate_schema import MealPlateUpdate
from models.meal_plate import MealPlate
from resources.ingredient_resource import IngredientResource

import time


load_dotenv()

class DosisResource:
    def __init__(self, session: Session):
        self.session = session
    
    def calculate(self, meal_plate_id: int, current_user: User = None): # Podría poner el mealplate en parámetros
        try:
            print("Calculando dosis para MealPlate:", meal_plate_id)

            clinical_resource = ClinicalDataResource(self.session, current_user=current_user)
            clinical_data = clinical_resource.get_by_user_id(current_user.id)

            if not clinical_data:
                raise HTTPException(status_code=400, detail="Datos clínicos no encontrados")

            ratio = clinical_data.ratio  # Asegúrate de que ratio existe
            sensitivity = clinical_data.sensitivity  # Asegúrate de que ratio existe


            # Si pongo en parámetros me salteo esta query
            meal_plate_resource = MealPlateResource(self.session)
            meal_plate = meal_plate_resource.get_by_id(meal_plate_id)  # Esto ahora lanzará 404 si no existe

            # Esta es 100% Necesaria
            ingredients_resource = IngredientResource(self.session)
            meal_plate_with_ingredients = ingredients_resource.read_ingredients_by_meal_plate(meal_plate_id)

            print("RESPUESTA BIEN: ", meal_plate_with_ingredients)

            # Calcular la suma de carbs
            total_carbs = sum(ingredient['carbs'] for ingredient in meal_plate_with_ingredients['ingredients'])

            # Calcular la dosis
            
            
            
            
            calculated_dosis = 0.0
            
            
            
            # 
            data = MealPlateUpdate(
                totalCarbs= total_carbs,
                dosis  = calculated_dosis
            )
            
            # 4. Actualizar el meal_plate con la dosis calculada
            meal_plate_resource.update(meal_plate_id, data)

            # return 

        except HTTPException as http_exc:
            print(f"Error HTTP en calculate_dosis: {http_exc.detail}")
            raise
        except Exception as e:
            print(f"Error inesperado en calculate_dosis: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error al calcular dosis: {str(e)}")