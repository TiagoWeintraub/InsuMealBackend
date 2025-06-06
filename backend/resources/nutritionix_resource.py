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
    
            # Verificar si el ingrediente ya existe en la base de datos
            ingredient_resource = IngredientResource(self.session)
            
            try:
                existing_ingredient = ingredient_resource.get_by_name(normalized_food)
                
                # Si el ingrediente ya existe, usamos sus datos directamente
                print(f"Ingrediente '{normalized_food}' encontrado en la base de datos")
                normalized_api_food_name = normalized_food
                carbs_per_hundred = existing_ingredient.carbsPerHundredGrams
                ingredientId = existing_ingredient.id
            except HTTPException as e:
                if e.status_code == 404:
                    # Si no existe, hacemos la petición a la API
                    print(f"Buscando ingrediente '{normalized_food}' en Nutritionix API")
                    food_data = self.post_food_by_natural_language(normalized_food, grams)
                    normalized_api_food_name = food_data["food_name"].lower()
                    carbs_per_hundred = food_data["carbs"]
    
                    # Creamos el ingrediente usando el nombre normalizado
                    self.create_ingredient(meal_plate.id, normalized_api_food_name, carbs_per_hundred)
                    
                    # Obtenemos el ID del ingrediente recién creado
                    new_ingredient = self.session.exec(
                        select(Ingredient).where(Ingredient.name == normalized_api_food_name)
                    ).first()
                    ingredientId = new_ingredient.id
                    
                    time.sleep(1)  # Se espera 1 segundo entre cada llamada a la API para evitar el rate limit
                else:
                    # Si es otro tipo de error, lo propagamos
                    raise e
    
            # Guardamos los datos en el diccionario
            name_and_carbs_dic[normalized_api_food_name] = {
                "carbs": carbs_per_hundred,
            }
    
            # Se actualiza la tabla MealPlateIngredient para que tenga los gramos y carbohidratos
            calculated_carbs = self.update_meal_plate_ingredient(carbs_per_hundred, grams, ingredientId, meal_plate.id)
    
            print(f"\n\nAlimento: {normalized_api_food_name}, Carbohidratos: {carbs_per_hundred}, Gramos: {grams}, Total: {calculated_carbs}g\n\n")
    
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
    
    def add_ingredient_to_meal_plate(self, ingredient_id: int, meal_plate_id: int):
        print("Agregando ingrediente al MealPlate en Nutritionix")

        resource = MealPlateIngredientResource(self.session, current_user=self.current_user)

        try:
            # Verifica si el ingrediente ya está asociado al MealPlate
            existing_ingredient = resource.get_one(meal_plate_id, ingredient_id)
            if existing_ingredient:
                print(f"El ingrediente {ingredient_id} ya está asociado al MealPlate {meal_plate_id}")
                return existing_ingredient
        except HTTPException as e:
            if e.status_code == 404:
                # Si no existe, lo creamos directamente en la base de datos
                print(f"Creando nueva relación MealPlateIngredient")

                # Crear un objeto MealPlateIngredient directamente
                from models.meal_plate_ingredient import MealPlateIngredient

                meal_plate_ingredient = MealPlateIngredient(
                    meal_plate_id=meal_plate_id,
                    ingredient_id=ingredient_id,
                    grams=0.0,  # Valores iniciales que serán actualizados después
                    carbs=0.0
                )

                self.session.add(meal_plate_ingredient)
                self.session.commit()
                self.session.refresh(meal_plate_ingredient)

                return meal_plate_ingredient
            else:
                raise e
        
    def update_meal_plate_ingredient(self, carbsPerHundredGrams: float, grams: float, ingredient_id: int, meal_plate_id: int):
        print("Actualizando MealPlateIngredient en Nutritionix")

        resource = MealPlateIngredientResource(self.session, current_user=self.current_user)

        carbs = round((carbsPerHundredGrams * grams) / 100, 2)

        # Primero verificamos si existe la relación
        try:
            # Intentamos obtener la relación existente
            existing_relation = resource.get_one(meal_plate_id, ingredient_id)

            # Si existe, la actualizamos
            data = MealPlateIngredientUpdate(
                grams=round(grams, 2),
                carbs=carbs
            )

            updated_ingredient = resource.update(meal_plate_id, ingredient_id, data)

        except HTTPException as e:
            # Si obtenemos un 404, significa que no existe la relación
            if e.status_code == 404:
                print(f"Creando nueva relación entre MealPlate {meal_plate_id} e Ingredient {ingredient_id}")

                # Creamos la relación utilizando el método que ya tenemos
                self.add_ingredient_to_meal_plate(ingredient_id, meal_plate_id)

                # Luego la actualizamos con los valores correctos
                data = MealPlateIngredientUpdate(
                    grams=round(grams, 2),
                    carbs=carbs
                )

                updated_ingredient = resource.update(meal_plate_id, ingredient_id, data)
            else:
                # Si es otro tipo de error, lo propagamos
                raise e

        return carbs

