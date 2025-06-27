from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import Dict, Any
from pydantic import BaseModel
import argostranslate.package
import argostranslate.translate

from database import get_session
from models.user import User
from auth.dependencies import get_current_user
from resources.nutritionix_resource import NutritionixResource
from resources.meal_plate_resource import MealPlateResource
from resources.ingredient_resource import IngredientResource
from models.meal_plate import MealPlate


def setup_translation_packages():
    """Configura y descarga los paquetes de traducción necesarios"""
    try:
        # Actualizar el índice de paquetes disponibles
        argostranslate.package.update_package_index()
        
        # Buscar el paquete de español a inglés
        available_packages = argostranslate.package.get_available_packages()
        spanish_to_english_package = None
        
        for package in available_packages:
            if package.from_code == "es" and package.to_code == "en":
                spanish_to_english_package = package
                break
        
        if spanish_to_english_package is None:
            print("Advertencia: No se encontró el paquete de traducción español-inglés")
            return False
        
        # Verificar si el paquete ya está instalado
        installed_packages = argostranslate.package.get_installed_packages()
        is_installed = any(
            pkg.from_code == "es" and pkg.to_code == "en" 
            for pkg in installed_packages
        )
        
        if not is_installed:
            print("Descargando e instalando paquete de traducción español-inglés...")
            argostranslate.package.install_from_path(
                spanish_to_english_package.download()
            )
            print("Paquete de traducción instalado exitosamente")
        else:
            print("Paquete de traducción español-inglés ya está instalado")
        
        return True
            
    except Exception as e:
        print(f"Error configurando paquetes de traducción: {e}")
        return False


def translate_spanish_to_english(text: str) -> str:
    """Traduce texto de español a inglés usando argostranslate"""
    try:
        # Traducir de español a inglés
        translated_text = argostranslate.translate.translate(text, "es", "en")
        print(f"Traducción: '{text}' -> '{translated_text}'")
        return translated_text.lower()
    except Exception as e:
        print(f"Error en la traducción: {e}")
        # Si falla la traducción, devolver el texto original en minúsculas
        return text.lower()


def translate_food_dictionary(food_dic: dict) -> dict:
    """Traduce todas las claves del diccionario de español a inglés"""
    # Configurar paquetes de traducción si es necesario
    setup_success = setup_translation_packages()
    if not setup_success:
        print("Advertencia: No se pudo configurar la traducción, usando nombres originales")
        return food_dic
    
    translated_food_dic = {}
    for spanish_key, grams in food_dic.items():
        english_key = translate_spanish_to_english(spanish_key)
        translated_food_dic[english_key] = grams
        print(f"Alimento traducido: '{spanish_key}' -> '{english_key}' ({grams}g)")
    
    return translated_food_dic


router = APIRouter(
    prefix="/nutrition"
)

@router.post("/add/food/{meal_plate_id}")
async def process_foods(meal_plate_id: int, food_dic: dict = {},current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
        nutritionix_resource = NutritionixResource(session, current_user)
        meal_plate = session.get(MealPlate, meal_plate_id)
        if not meal_plate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MealPlate no encontrado")
        
        # Traducir el diccionario de alimentos de español a inglés
        translated_food_dic = translate_food_dictionary(food_dic)
        
        # Procesar los alimentos traducidos y agregarlos al meal plate
        result = nutritionix_resource.orquest(translated_food_dic, meal_plate)

        # Obtener la información completa del meal plate con todos sus ingredientes
        ingredient_resource = IngredientResource(session)
        meal_plate_details = ingredient_resource.read_ingredients_by_meal_plate(meal_plate_id)

        return meal_plate_details

