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
    def __init__(self, session: Session, current_user: User = None):
        self.current_user = current_user
        self.session = session
    
    def calculate(self, current_user: User = None): # Calcular la dosis 
        try:
            # Busca el último MealPlate creado del usuario
            meal_plate_resource = MealPlateResource(self.session)
            meal_plate = meal_plate_resource.get_last_by_user_id(current_user.id)
            
            print("Calculando dosis para MealPlate:", meal_plate.id)

            clinical_resource = ClinicalDataResource(self.session, current_user=current_user)
            clinical_data = clinical_resource.get_by_user_id(current_user.id)

            if not clinical_data:
                raise HTTPException(status_code=400, detail="Datos clínicos no encontrados")

            ratio = clinical_data.ratio  # Asegúrate de que ratio existe
            sensitivity = clinical_data.sensitivity  # Asegúrate de que ratio existe



            # Traigo los datos de ClinicalData
            clinical_data = clinical_resource.get_by_user_id(current_user.id)
            if not clinical_data:
                raise HTTPException(status_code=400, detail="Datos clínicos no encontrados")
            
            ratio = clinical_data.ratio
            sensitivity = clinical_data.sensitivity
            glycemic_target = clinical_data.glycemicTarget

            # Obtenemos el total de carbohidratos del MealPlate 
            total_carbs = meal_plate.totalCarbs

            # Calcular la dosis
            
            
            
            
            calculated_dosis = 0.0
            
            
            
            # 
            data = MealPlateUpdate(
                totalCarbs= total_carbs,
                dosis  = calculated_dosis
            )
            
            # 4. Actualizar el meal_plate con la dosis calculada
            meal_plate_resource.update(meal_plate.id, data)

            # return 

        except HTTPException as http_exc:
            print(f"Error HTTP en calculate_dosis: {http_exc.detail}")
            raise
        except Exception as e:
            print(f"Error inesperado en calculate_dosis: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error al calcular dosis: {str(e)}")