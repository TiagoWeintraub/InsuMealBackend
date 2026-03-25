import os
import logging
from dotenv import load_dotenv
import requests
from sqlmodel import Session, select
from fastapi import HTTPException
from resources.ingredient_resource import IngredientResource
from models.food_history import FoodHistory
from models.user import User
from schemas.ingredient_schema import IngredientCreate
from models.meal_plate import MealPlate
from models.ingredient import Ingredient
from resources.meal_plate_ingredient_resource import MealPlateIngredientResource
from schemas.meal_plate_ingredient_schema import MealPlateIngredientUpdate
from models.meal_plate_ingredient import MealPlateIngredient
from utils.json_dict_converter import json_to_dict
import time

logger = logging.getLogger(__name__)
load_dotenv()


class EdamamResource:
    def __init__(self, session: Session, current_user: User = None):
        self.current_user = current_user
        self.session = session
        self.app_id = os.getenv("EDAMAM_APP_ID")
        self.app_key = os.getenv("EDAMAM_APP_KEY")
        self.page_size = 1
        if not self.app_id or not self.app_key:
            raise ValueError("EDAMAM_APP_ID o EDAMAM_APP_KEY no están definidos en el .env")
        self.base_url = os.getenv("EDAMAM_URL")

    def get_food_by_name(self, food_name: str) -> dict:
        """Obtiene food_id y label del alimento. Para carbohidratos usar post_food_by_natural_language."""
        logger.debug(f"Consultando Edamam para: {food_name}")
        url = f"{self.base_url}/parser?app_id={self.app_id}&app_key={self.app_key}&ingr={food_name}&pageSize={self.page_size}"
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Error en Edamam API: {response.status_code} - {response.text}")
            raise Exception(f"Error en la búsqueda: {response.status_code} - {response.text}")

        food_data = response.json()
        if food_data.get("parsed") and len(food_data["parsed"]) > 0:
            food_item = food_data["parsed"][0]["food"]
        elif food_data.get("hints") and len(food_data["hints"]) > 0:
            food_item = food_data["hints"][0]["food"]
        else:
            logger.warning(f"Alimento no encontrado en Edamam: {food_name}")
            raise HTTPException(status_code=404, detail="Alimento no encontrado")

        return {
            "food_id": food_item.get("foodId"),
            "label": food_item.get("label"),
            "category": food_item.get("category"),
        }

    def search_carbs_by_food_id(self, food_id: str, grams: float = 100.0) -> dict:
        """Obtiene nutrientes para una cantidad dada en gramos. Por defecto 100g (carbohidratos por 100g)."""
        logger.debug(f"Buscando nutrientes en Edamam para food_id: {food_id}, {grams}g")
        url = f"{self.base_url}/nutrients?app_id={self.app_id}&app_key={self.app_key}"
        payload = {
            "ingredients": [
                {
                    "quantity": grams,
                    "measure": "gram",
                    "foodId": food_id,
                }
            ]
        }
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            raise Exception(f"Error en la búsqueda: {response.status_code} - {response.text}")
        return response.json()

    def post_food_by_natural_language(self, food_name: str, grams: float = 100.0) -> dict:
        """Devuelve food_name y carbohidratos (por 100 g) para un alimento."""
        logger.debug(f"Consultando Edamam para: {food_name}")
        food_data = self.get_food_by_name(food_name)
        nutrients = self.search_carbs_by_food_id(food_data["food_id"], grams=100.0)
        carbs = nutrients.get("totalNutrients", {}).get("CHOCDF", {}).get("quantity")
        if carbs is None:
            carbs = 0.0
        return {
            "food_name": food_data["label"],
            "carbs": round(float(carbs), 2),
        }

    def orquest(self, food_dic, meal_plate: MealPlate = None) -> MealPlate:
        """Procesa food_dic { nombre: gramos } y actualiza el plato con ingredientes y carbos."""
        logger.info(f"Iniciando procesamiento nutricional (Edamam) para {len(food_dic) if isinstance(food_dic, dict) else 'datos'} alimentos")
        if isinstance(food_dic, str):
            food_dic = json_to_dict(food_dic)

        for key in food_dic.keys():
            normalized_food = key.lower()
            grams = food_dic[key]

            ingredient_resource = IngredientResource(self.session)
            try:
                existing_ingredient = ingredient_resource.get_by_name(normalized_food)
                logger.debug(f"Ingrediente '{normalized_food}' encontrado en BD")
                normalized_api_food_name = normalized_food
                carbs_per_hundred = existing_ingredient.carbsPerHundredGrams
                ingredient_id = existing_ingredient.id
            except HTTPException as e:
                if e.status_code == 404:
                    logger.info(f"Consultando Edamam para nuevo ingrediente: '{normalized_food}'")
                    food_data = self.post_food_by_natural_language(normalized_food, grams)
                    normalized_api_food_name = food_data["food_name"].lower()
                    carbs_per_hundred = food_data["carbs"]

                    self.create_ingredient(meal_plate.id, normalized_api_food_name, carbs_per_hundred)
                    new_ingredient = self.session.exec(
                        select(Ingredient).where(Ingredient.name == normalized_api_food_name)
                    ).first()
                    ingredient_id = new_ingredient.id

                    time.sleep(1)
                    logger.debug("Rate limit: esperando 1 segundo")
                else:
                    logger.error(f"Error inesperado al buscar ingrediente '{normalized_food}': {e}")
                    raise e

            self.update_meal_plate_ingredient(carbs_per_hundred, grams, ingredient_id, meal_plate.id)
            logger.info(f"Procesado: {normalized_api_food_name} - {round((carbs_per_hundred * grams) / 100, 2)}g carbohidratos ({grams}g porción)")

        logger.info("Procesamiento nutricional (Edamam) completado exitosamente")
        return meal_plate

    def create_ingredient(self, meal_plate_id: int, name: str, carbs: float) -> dict:
        ingredient_resource = IngredientResource(self.session)
        ingredient_data = IngredientCreate(
            name=name,
            carbsPerHundredGrams=carbs,
            meal_plate_id=meal_plate_id,
        )
        ingredient_resource.create(ingredient_data)
        logger.info(f"Ingrediente creado: {name} ({carbs}g carbohidratos/100g)")
        return {"message": "Ingrediente creado exitosamente"}

    def add_ingredient_to_meal_plate(self, ingredient_id: int, meal_plate_id: int):
        logger.debug(f"Agregando ingrediente {ingredient_id} a MealPlate {meal_plate_id}")
        resource = MealPlateIngredientResource(self.session, current_user=self.current_user)
        try:
            existing_ingredient = resource.get_one(meal_plate_id, ingredient_id)
            if existing_ingredient:
                logger.debug(f"El ingrediente {ingredient_id} ya está asociado al MealPlate {meal_plate_id}")
                return existing_ingredient
        except HTTPException as e:
            if e.status_code == 404:
                logger.debug(f"Creando nueva relación MealPlateIngredient para ingrediente {ingredient_id}")
                meal_plate_ingredient = MealPlateIngredient(
                    meal_plate_id=meal_plate_id,
                    ingredient_id=ingredient_id,
                    grams=0.0,
                    carbs=0.0,
                )
                self.session.add(meal_plate_ingredient)
                self.session.commit()
                self.session.refresh(meal_plate_ingredient)
                return meal_plate_ingredient
            raise e

    def update_meal_plate_ingredient(
        self, carbs_per_hundred_grams: float, grams: float, ingredient_id: int, meal_plate_id: int
    ) -> float:
        logger.debug(f"Actualizando MealPlateIngredient: {grams}g, ingrediente {ingredient_id}")
        resource = MealPlateIngredientResource(self.session, current_user=self.current_user)
        carbs = round((carbs_per_hundred_grams * grams) / 100, 2)

        try:
            existing_relation = resource.get_one(meal_plate_id, ingredient_id)
            data = MealPlateIngredientUpdate(grams=round(grams, 2), carbs=carbs)
            resource.update(meal_plate_id, ingredient_id, data)
        except HTTPException as e:
            if e.status_code == 404:
                logger.debug(f"Creando nueva relación MealPlate {meal_plate_id} - Ingredient {ingredient_id}")
                self.add_ingredient_to_meal_plate(ingredient_id, meal_plate_id)
                data = MealPlateIngredientUpdate(grams=round(grams, 2), carbs=carbs)
                resource.update(meal_plate_id, ingredient_id, data)
            else:
                logger.error(f"Error inesperado al actualizar MealPlateIngredient: {e}")
                raise e
        return carbs
