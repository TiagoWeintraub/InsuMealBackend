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

class UsdaResource:
    def __init__(self, session: Session, current_user: User = None):
        self.current_user = current_user
        self.session = session
        self.app_key = os.getenv("USDA_API_KEY")
        self.data_type = 'SR Legacy'
        self.page_size =1
        if not self.app_key:
            raise ValueError("USDA_APP_KEY no están definidos en el .env")
        self.base_url = os.getenv("USDA_URL")

    def get_food_by_name(self, food_name: str):
        print("Get para buscar carbohidratos por nombre")
        url = f"{self.base_url}api_key={self.app_key}&query={food_name}&dataType={self.data_type}&pageSize={self.page_size}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Error en la búsqueda: {response.status_code} - {response.text}")
    
        food_data = response.json()
        print("Respuesta de USDA recibida", food_data)
    
        # Verifica si existen resultados en 'foods'
        if food_data.get("foods") and len(food_data["foods"]) > 0:
            food_item = food_data["foods"][0]  # Toma el primer resultado
            # Busca el nutriente con "nutrientId": 1005 en la lista de nutrientes
            
            name= food_name
            
            carbs = next(
                (nutrient["value"] for nutrient in food_item.get("foodNutrients", [])
                if nutrient.get("nutrientId") == 1005),
                None  # Valor por defecto si no se encuentra el nutriente
            )
            
            # Busca la unidad de medida de los carbohidratos, dentro del JSON donde se encuentran los carbohidratos sale la clave "unitName"
            carbsUnit = next(
                (nutrient["unitName"] for nutrient in food_item.get("foodNutrients", [])
                if nutrient.get("nutrientId") == 1005),
                "G"  # Valor por defecto si no se encuentra la unidad
            )
            
            print("Nombre: " ,"Carbohidratos encontrados: ", carbs, "Unidad: ", carbsUnit)
            return {
                "name": food_name,
                "carbs": carbs,
                # Unit
                "unit": carbsUnit,
            }
        else:
            print("No se encontraron resultados para el alimento:", food_name)
            raise HTTPException(status_code=404, detail="Alimento no encontrado")

    def orquest(self, food_dic):  # Sirve para ejecutar primero el get_food_by_name y luego el search_carbs_by_food_id
        print("Iniciando la orquestación de Edamam")
        name_carbs_dic = {}
        for key in food_dic.keys():
            try:
                # Normaliza el nombre de búsqueda a minúsculas
                normalized_key = key.lower()
                # Llama a la función get_food_by_name usando el nombre normalizado
                usda_food_data = self.get_food_by_name(normalized_key)

                # Normaliza el label recibido para que coincida
                normalized_name = usda_food_data["name"].lower()
                name_carbs_dic[normalized_name] = {
                    "carbs": usda_food_data["carbs"]
                }

                # Se crea el ingrediente usando el nombre normalizado
                self.create_ingredient(normalized_name, usda_food_data["carbs"])
                print("Alimento:", normalized_name, "Carbohidratos:", usda_food_data["carbs"], "Unidad:", usda_food_data["unit"])
                return name_carbs_dic

            except Exception as e:
                print(f"Error al procesar el alimento {key}: {e}")
                raise HTTPException(status_code=500, detail=f"Error al procesar el alimento {key}: {e}")


    def create_ingredient(self, name: str, carbs: float):
        ingredient_resource = IngredientResource(self.session)
        
        # Obtener el FoodHistory asociado al usuario actual
        food_history = self.session.exec(
            select(FoodHistory).where(FoodHistory.user_id == self.current_user.id)
        ).first()
        if not food_history:
            raise HTTPException(status_code=404, detail="FoodHistory no encontrado para el usuario.")
        
        # Buscar el MealPlate asociado al FoodHistory obtenido
        try:
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
            self.session.commit()
            print("Ingrediente creado:", name, "Carbohidratos:", carbs)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al crear el ingrediente: {str(e)}")