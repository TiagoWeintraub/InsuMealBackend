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
    
    def calculate(self, current_user: User = None, glycemia: float = None):
        try:
            # Verifica la validez de la glucemia
            if glycemia is None or glycemia < 0 or glycemia > 500:
                raise HTTPException(status_code=400, detail="Glycemia no válida")
            
            # Usa el usuario del objeto si no se proporciona uno
            user = current_user if current_user else self.current_user
            
            if not user or not user.id:
                raise HTTPException(status_code=400, detail="Usuario no válido o no autenticado")
            
            # Busca el último MealPlate creado del usuario
            meal_plate_resource = MealPlateResource(self.session)
            try:
                meal_plate = meal_plate_resource.get_last_by_user_id(user.id)
                if not meal_plate:
                    raise HTTPException(status_code=404, detail="No se encontró un MealPlate reciente para calcular la dosis")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error al obtener el último MealPlate: {str(e)}")

            clinical_resource = ClinicalDataResource(self.session, current_user=user)
            clinical_data = clinical_resource.get_by_user_id(user.id)
            
            if not clinical_data:
                raise HTTPException(status_code=400, detail="Datos clínicos no encontrados")
            
            ratio = clinical_data.ratio
            sensitivity = clinical_data.sensitivity
            glycemia_target = clinical_data.glycemiaTarget
    
            # Obtenemos el total de carbohidratos del MealPlate 
            total_carbs = meal_plate.totalCarbs
            
            if not total_carbs:
                raise HTTPException(status_code=400, detail="El MealPlate no tiene carbohidratos registrados")
    
            # Calcular la insulina necesaria para corregir la glucosa (Sensibilidad)
            correction_insulin = (glycemia - glycemia_target) / sensitivity 
            
            # Calcular la insulina necesaria para los carbohidratos (Ratio)
            carb_insulin = total_carbs / ratio
            
            # Dosis total de insulina
            total_dosis = round(correction_insulin + carb_insulin, 2)
    
            data = MealPlateUpdate(
                dosis = total_dosis,
                glycemia = glycemia
            )
    
            meal_plate_resource.update(meal_plate.id, data)
            
            return {"dosis": total_dosis, "glycemia": glycemia}
            
        except HTTPException as http_exc:
            raise
        except Exception as e:
            print(f"Error inesperado en calculate_dosis: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error al calcular dosis: {str(e)}")