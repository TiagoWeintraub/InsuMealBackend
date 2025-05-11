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
from resources.meal_plate_resource import MealPlateResource
from models.ingredient import Ingredient
from schemas.meal_plate_ingredient_schema import MealPlateIngredientUpdate
from resources.dosis_resource import DosisResource
from utils.json_dict_converter import dict_to_json, json_to_dict
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


    def orquest(self, food_dic, meal_plate: MealPlate = None):  
        print("Iniciando la orquestación de nutritionix")
        name_and_carbs_dic = {}
        
        # Si food_dic es un json, lo convierte a un diccionario
        if isinstance(food_dic, str):
            food_dic = json_to_dict(food_dic)

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
            self.create_ingredient(meal_plate.id,normalized_api_food_name, food_data["carbs"])
            
            # Obtiene el ID del ingrediente creado
            ingredientId = self.session.exec(
                select(Ingredient).where(Ingredient.name == normalized_api_food_name)
            ).first()
            
            # se actualiza la tabla MealPlateIngredient para que tenga los gramos y carbohidratos
            self.update_meal_plate_ingredient(food_data["carbs"], grams, ingredientId.id, meal_plate.id)
            
            print("\n\nAlimento:", normalized_api_food_name, "Carbohidratos:", food_data["carbs"],"\n\n")
            
            
            time.sleep(1) # Se espera 1 segundo entre cada llamada a la API para evitar el rate limit
        
        # Se actualiza el total de carbohidratos en la tabla MealPlate
        self.update_meal_plate_total_carbs(meal_plate.id)
        
        
        # self.calculate_dosis(meal_plate.id)
        
        return meal_plate



    def create_ingredient(self, meal_plate_id, name: str, carbs: float):
        ingredient_resource = IngredientResource(self.session)
        
        ingredient_data = IngredientCreate(
            name=name, 
            carbsPerHundredGrams=carbs,
            meal_plate_id=meal_plate_id
        )
        
        ingredient_resource.create(ingredient_data)
        print("Ingrediente ", name, "Creado exitosamente")
        return {"message": "Ingrediente creado exitosamente"}

    def update_meal_plate_ingredient(self, carbsPerHundredGrams: float, grams: float, ingredient_id: int, meal_plate_id: int):
        print("Actualizando MealPlateIngredient en Nutritionix")
        
        resource = MealPlateIngredientResource(self.session, current_user=self.current_user)
        
        carbs = round((carbsPerHundredGrams * grams) / 100, 2)
                
        data = MealPlateIngredientUpdate(
            grams=round(grams, 2),
            carbs=carbs
        )

        updated_ingredient = resource.update(meal_plate_id, ingredient_id, data)

        return carbs 
    
    def update_meal_plate_total_carbs(self, meal_plate_id: int):
        print("Actualizando el total de carbs del MealPlate")
        meal_plate_resource = MealPlateResource(self.session)
        total_carbs = meal_plate_resource.calculate_total_carbs(meal_plate_id)
        if not total_carbs:
            raise HTTPException(status_code=404, detail="MealPlate no encontrado")
        # Actualiza el total de carbohidratos en el MealPlate

        return {"Ingrediente agregado correctamente"}
