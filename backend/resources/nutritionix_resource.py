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
from resources.meal_plate_ingredient_resource import MealPlateIngredientResource
from models.ingredient import Ingredient
from schemas.meal_plate_ingredient_schema import MealPlateIngredientUpdate
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
        
        formated_query = f"100 grams of {food_name}" 

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


    def orquest(self, food_dic, meal_plate_id: int):  
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
            self.create_ingredient(meal_plate_id,normalized_api_food_name, food_data["carbs"])
            
            # Obtiene el ID del ingrediente creado
            ingredientId = self.session.exec(
                select(Ingredient).where(Ingredient.name == normalized_api_food_name)
            ).first()
            
            # se actualiza la tabla MealPlateIngredient para que tenga los gramos y carbohidratos
            self.update_meal_plate_ingredient(meal_plate_id, normalized_api_food_name, food_data["carbs"], grams, ingredientId.id)
            
            print("\n\nAlimento:", normalized_api_food_name, "Carbohidratos:", food_data["carbs"],"\n\n")


    def create_ingredient(self, meal_plate_id, name: str, carbs: float):
        ingredient_resource = IngredientResource(self.session)
        
        # Obtener el FoodHistory asociado al usuario actual
        food_history = self.session.exec(
            select(FoodHistory).where(FoodHistory.user_id == self.current_user.id)
        ).first()
        if not food_history:
            raise HTTPException(status_code=404, detail="FoodHistory no encontrado para el usuario.")
        
        # Buscar el MealPlate asociado al FoodHistory obtenido
        
        
        ingredient_data = IngredientCreate(
            name=name, 
            carbsPerHundredGrams=carbs,
            meal_plate_id=meal_plate_id
        )
        
        ingredient_resource.create(ingredient_data)
        return {"message": "Ingrediente creado exitosamente"}

    def update_meal_plate_ingredient(self,meal_plate_id, food_name: str, carbsPerHundredGrams: float, grams: float, ingredient_id: int):
        print("Actualizando MealPlateIngredient")
        
        resource = MealPlateIngredientResource(self.session)
        
        carbs = round((carbsPerHundredGrams * grams) / 100, 2)
                
        data = MealPlateIngredientUpdate(
            grams=round(grams, 2),
            carbs=carbs
        )
        updated_ingredient = resource.update(meal_plate_id, ingredient_id, data)
        return {"\nmessage": "MealPlateIngredient actualizado exitosamente. Hay {carbs} gramos de carbohidratos en {grams} gramos de {food_name}", "data": updated_ingredient}