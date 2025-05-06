import os 
import io
from dotenv import load_dotenv
import requests
from sqlmodel import Session, select
from fastapi import HTTPException
from resources.ingredient_resource import IngredientResource
from models.food_history import FoodHistory
from models.user import User
from schemas.ingredient_schema import IngredientCreate
from models.meal_plate import MealPlate
from models.food_history import FoodHistory
import time


load_dotenv()

class NutritionixResource:
    def __init__(self, session: Session, current_user: User = None):
        self.current_user = current_user
        self.session = session
        self.app_id = os.getenv("NUTRITIONIX_APP_ID")
        self.app_key = os.getenv("NUTRITIONIX_APP_KEY") 
        self.page_size =1
        if not self.app_id or not self.app_key:
            raise ValueError("NUTRITIONIX_APP_ID o NUTRITIONIX_APP_KEY no están definidos en el .env")
        self.base_url = os.getenv("NUTRITIONIX_URL")

    def post_food_by_natural_language(self, food_name: str, grams: float = 100.00):
        print("Post para buscar carbohidratos por nombre")
        url = f"{self.base_url}"    
        
        formated_query = f"{grams} grams of {food_name}" 

        headers = {
            "x-app-id": self.app_id,
            "x-app-key": self.app_key,
            "Content-Type": "application/json"
        }
        payload = {
            "query": formated_query,
        }
        
        response = requests.post(url, headers=headers, json=payload)
        print("Respuesta de nutritionix recibida")

        if response.status_code != 200:
            raise Exception(f"Error en la búsqueda: {response.status_code} - {response.text}")

        food_data = response.json()
        print("Respuesta de nutritionix recibida", food_data)

        # Verifica si existen resultados en la respuesta
        if food_data.get("foods") and len(food_data["foods"]) > 0:
            food_item = food_data["foods"][0]

        return {
            "food_name": food_item.get("food_name"),
            "carbs": food_item.get("nf_total_carbohydrate")
            }


    def orquest(self, food_dic):  
        print("Iniciando la orquestación de nutritionix")
        name_and_carbs_dic = {}
        
        for key in food_dic.keys():

            normalized_food = key.lower()
            grams = food_dic[key]
            
            # Llama a la función get_food_by_name usando el nombre normalizado
            food_data = self.post_food_by_natural_language(normalized_food, grams)
            
            # Normaliza el nombre recibido de la API
            normalized_api_food_name = food_data["food_name"].lower()
            name_and_carbs_dic[normalized_api_food_name] = {
                "carbs": food_data["carbs"],
            }

            # Se crea el ingrediente usando el nombre normalizado
            self.create_ingredient(normalized_api_food_name, food_data["carbs"])
            
            print("\n\nAlimento:", normalized_api_food_name, "Carbohidratos:", food_data["carbs"],"\n\n")


    def create_ingredient(self, name: str, carbs: float):
        ingredient_resource = IngredientResource(self.session)
        
        # Obtener el FoodHistory asociado al usuario actual
        food_history = self.session.exec(
            select(FoodHistory).where(FoodHistory.user_id == self.current_user.id)
        ).first()
        if not food_history:
            raise HTTPException(status_code=404, detail="FoodHistory no encontrado para el usuario.")
        
        # Buscar el MealPlate asociado al FoodHistory obtenido
        meal_plate = self.session.exec(
            select(MealPlate).where(MealPlate.food_history_id == food_history.id)
        ).first()
        if not meal_plate:
            raise HTTPException(status_code=404, detail="No se encontró el último MealPlate creado.")
        
        ingredient_data = IngredientCreate(
            name=name, 
            carbsPerHundredGrams=carbs,
            meal_plate_id=meal_plate.id
        )
        
        ingredient_resource.create(ingredient_data)
        return {"message": "Ingrediente creado exitosamente"}

