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
from models.ingredient import Ingredient
from models.meal_plate import MealPlate
from models.food_history import FoodHistory


load_dotenv()

class EdamamResource:
    def __init__(self, session: Session, current_user: User = None):
        self.current_user = current_user
        self.session = session
        self.app_id = os.getenv("EDAMAM_APP_ID")
        self.app_key = os.getenv("EDAMAM_APP_KEY")
        self.page_size =1
        if not self.app_id or not self.app_key:
            raise ValueError("EDAMAM_APP_ID o EDAMAM_APP_KEY no están definidos en el .env")
        self.base_url = os.getenv("EDAMAM_URL")

    def get_food_by_name(self, food_name: str):
        print("Get para buscar carbohidratos por nombre")
        url = f"{self.base_url}/parser?app_id={self.app_id}&app_key={self.app_key}&ingr={food_name}&pageSize={self.page_size}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Error en la búsqueda: {response.status_code} - {response.text}")

        food_data = response.json()
        print("Respuesta de Edamam recibida", food_data)

        # Verifica si existen resultados en 'parsed' o, en su defecto, en 'hints'
        if food_data.get("parsed") and len(food_data["parsed"]) > 0:
            food_item = food_data["parsed"][0]["food"]
        elif food_data.get("hints") and len(food_data["hints"]) > 0:
            food_item = food_data["hints"][0]["food"]
        else:
            print("No se encontraron resultados para el alimento:", food_name)
            raise HTTPException(status_code=404, detail="Alimento no encontrado")

        return {
            "food_id": food_item.get("foodId"),
            "label": food_item.get("label"),
            "category": food_item.get("category")
        }

    def search_carbs_by_food_id(self, food_id: str):
        print("Post para buscar carbohidratos por ID de alimento")
        url = f"{self.base_url}/nutrients?app_id={self.app_id}&app_key={self.app_key}"
        payload = {
            "ingredients": [
                {
                    "quantity": 100,
                    "measure": "gram",
                    "foodId": food_id
                }
            ]
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error en la búsqueda: {response.status_code} - {response.text}")

    def orquest(self, food_dic):  # Sirve para ejecutar primero el get_food_by_name y luego el search_carbs_by_food_id
        print("Iniciando la orquestación de Edamam")
        name_carbs_dic = {}
        for key in food_dic.keys():
            # Normaliza el nombre de búsqueda a minúsculas
            normalized_key = key.lower()
            # Llama a la función get_food_by_name usando el nombre normalizado
            food_data = self.get_food_by_name(normalized_key)
            # Luego llama a search_carbs_by_food_id
            carbs_data = self.search_carbs_by_food_id(food_data["food_id"])
            # Normaliza el label recibido para que coincida
            normalized_label = food_data["label"].lower()
            name_carbs_dic[normalized_label] = {
                "carbs": carbs_data["totalNutrients"]["CHOCDF"]["quantity"]
            }

            # Se crea el ingrediente usando el nombre normalizado
            self.create_ingredient(normalized_label, carbs_data["totalNutrients"]["CHOCDF"]["quantity"])
            print("Alimento:", normalized_label, "Carbohidratos:", carbs_data["totalNutrients"]["CHOCDF"]["quantity"])



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