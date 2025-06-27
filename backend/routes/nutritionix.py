from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import Dict, Any
from pydantic import BaseModel
import argostranslate.package
import argostranslate.translate
import google.generativeai as genai
import os
import json
import re

from database import get_session
from models.user import User
from auth.dependencies import get_current_user
from resources.nutritionix_resource import NutritionixResource
from resources.meal_plate_resource import MealPlateResource
from resources.ingredient_resource import IngredientResource
from models.meal_plate import MealPlate


class SingleFoodRequest(BaseModel):
    food: str  # Un solo alimento sin peso especificado


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
    """Traduce todas las claves del diccionario de alimentos de español a inglés"""
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


def setup_gemini():
    """Configura Gemini AI"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no está definido en el .env")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash-lite")


def estimate_food_portions_with_gemini(food_list: list, meal_plate_name: str) -> dict:
    """Usa Gemini para estimar las porciones típicas de alimentos en un plato específico"""
    try:
        model = setup_gemini()
        
        # Crear el prompt para Gemini
        foods_text = ", ".join(food_list)
        
        prompt = f"""
You are an expert in nutrition and food portions. I need you to estimate the typical amounts in grams of the following foods when they appear on a "{meal_plate_name}" plate.

Foods: {foods_text}

Please provide a realistic estimate of the grams of each food item that would typically be served in this type of dish. Consider standard servings for an adult.

Please respond ONLY in valid JSON format, without additional text, with this exact structure:
{{
"food1": amount_in_grams,
"food2": amount_in_grams
}}

Sample response:
{{
    "rice": 150,
    "chicken": 120,
    "broccoli": 60
}}
"""
        
        print(f"Consultando a Gemini para estimar porciones en plato '{meal_plate_name}'")
        response = model.generate_content(prompt)
        
        # Limpiar y parsear la respuesta
        clean_response = clean_gemini_response(response.text)
        estimated_portions = json.loads(clean_response)
        
        print(f"Porciones estimadas por Gemini: {estimated_portions}")
        return estimated_portions
        
    except Exception as e:
        print(f"Error estimando porciones con Gemini: {e}")
        # Si falla, retornar porciones por defecto
        default_portions = {food: 100 for food in food_list}
        print(f"Usando porciones por defecto: {default_portions}")
        return default_portions


def clean_gemini_response(response_text: str) -> str:
    """Limpia la respuesta de Gemini para extraer solo el JSON válido"""
    # Buscar el JSON en la respuesta
    json_pattern = r'\{[^{}]*\}'
    matches = re.findall(json_pattern, response_text)
    
    if matches:
        return matches[0]
    
    # Si no encuentra JSON, intentar extraer líneas que parezcan JSON
    lines = response_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            return line
    
    # Si todo falla, retornar un JSON vacío
    return "{}"


router = APIRouter(
    prefix="/nutrition"
)

@router.post("/add/food/{meal_plate_id}")
async def process_single_food(
    meal_plate_id: int, 
    request: SingleFoodRequest,  # Modelo Pydantic para un solo alimento
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    """
    Endpoint que recibe UN SOLO alimento (sin peso) y usa Gemini para estimar la porción automáticamente
    """
    # Inicializar variables para capturar en caso de error
    food_name = "Unknown"
    translated_food = None
    
    try:
        # Extraer y validar el nombre del alimento PRIMERO
        food_name = request.food.strip() if request.food else "Unknown"
        if not food_name or food_name == "Unknown":
            raise HTTPException(status_code=400, detail="El nombre del alimento no puede estar vacío")
        
        print(f"Alimento original recibido: '{food_name}'")
        
        nutritionix_resource = NutritionixResource(session, current_user)
        meal_plate = session.get(MealPlate, meal_plate_id)
        if not meal_plate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MealPlate no encontrado")
        
        # 1. TRADUCIR el alimento de español a inglés
        translated_food = translate_spanish_to_english(food_name)
        print(f"Alimento traducido: '{food_name}' -> '{translated_food}'")
        
        # 2. VERIFICAR si el alimento ya existe en el plato
        ingredient_resource = IngredientResource(session)
        try:
            # Intentar obtener el ingrediente por nombre traducido
            existing_ingredient = ingredient_resource.get_by_name(translated_food)
            
            # Si el ingrediente existe, verificar si ya está en el meal plate
            meal_plate_details = ingredient_resource.read_ingredients_by_meal_plate(meal_plate_id)
            existing_ingredient_ids = [ing["id"] for ing in meal_plate_details["ingredients"]]
            
            if existing_ingredient.id in existing_ingredient_ids:
                raise HTTPException(
                    status_code=409,  # Conflict
                    detail={
                        "error_type": "FOOD_ALREADY_EXISTS",
                        "message": f"El alimento '{food_name}' ya está en este plato",
                        "original_food": food_name,
                        "translated_food": translated_food,
                        "ingredient_id": existing_ingredient.id,
                        "suggestion": "El alimento ya fue agregado previamente a este plato"
                    }
                )
        except HTTPException as e:
            # Si es error 404 (ingrediente no existe), continuar normalmente
            if e.status_code == 404:
                print(f"Ingrediente '{translated_food}' no existe en BD, se creará uno nuevo")
            # Si es error 409 (ya existe en el plato), re-lanzar
            elif e.status_code == 409:
                raise e
            else:
                raise e
        
        # 3. USAR GEMINI para estimar la porción basándose en el tipo de meal plate
        estimated_portions = estimate_food_portions_with_gemini([translated_food], meal_plate.type)
        print(f"Porciones estimadas por Gemini: {estimated_portions}")
        
        # 4. CREAR DICCIONARIO con nombre traducido y peso estimado
        food_with_weight = {translated_food: estimated_portions.get(translated_food, 100)}
        print(f"Diccionario final que se enviará a Nutritionix: {food_with_weight}")
        
        # 5. ENVIAR A NUTRITIONIX el diccionario con alimento traducido y peso estimado
        result = nutritionix_resource.orquest(food_with_weight, meal_plate)

        # Obtener la información completa del meal plate con todos sus ingredientes
        ingredient_resource = IngredientResource(session)
        meal_plate_details = ingredient_resource.read_ingredients_by_meal_plate(meal_plate_id)

        return {
            "message": "Alimento procesado exitosamente",
            "original_food": food_name,
            "translated_food": translated_food,
            "estimated_weight": estimated_portions.get(translated_food, 100),
            "meal_plate_details": meal_plate_details
        }
        
    except Exception as e:
        print(f"Error en process_single_food: {str(e)}")
        print(f"food_name capturado: '{food_name}'")
        print(f"translated_food capturado: '{translated_food}'")
        
        # Verificar si es un error específico de Nutritionix (alimento no encontrado)
        error_message = str(e)
        if "We couldn't match any of your foods" in error_message or ("404" in error_message and "nutritionix" in error_message.lower()):
            raise HTTPException(
                status_code=404,
                detail={
                    "error_type": "FOOD_NOT_FOUND",
                    "message": f"Alimento '{food_name}' no encontrado en la base de datos nutricional",
                    "original_food": food_name,
                    "translated_food": translated_food,
                    "suggestion": "Intenta con un nombre más específico o común del alimento"
                }
            )
        
        # Si es un HTTPException, manejar casos específicos
        if isinstance(e, HTTPException):
            # Error específico de MealPlate no encontrado
            if e.status_code == 404 and "meal_plate" in str(e.detail).lower():
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error_type": "MEAL_PLATE_NOT_FOUND",
                        "message": f"MealPlate con ID {meal_plate_id} no encontrado",
                        "meal_plate_id": meal_plate_id,
                        "original_food": food_name,
                        "suggestion": "Verifica que el ID del plato sea correcto"
                    }
                )
            # Error de validación de alimento vacío
            elif e.status_code == 400:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_type": "VALIDATION_ERROR",
                        "message": str(e.detail),
                        "original_food": food_name
                    }
                )
            # Para otros HTTPException, agregar contexto
            else:
                raise HTTPException(
                    status_code=e.status_code,
                    detail={
                        "error_type": "HTTP_ERROR",
                        "message": str(e.detail),
                        "original_food": food_name,
                        "translated_food": translated_food
                    }
                )
            
        # Para otros errores, devolver un error más informativo
        raise HTTPException(
            status_code=500, 
            detail={
                "error_type": "INTERNAL_ERROR",
                "message": "Error interno procesando el alimento",
                "original_food": food_name,
                "translated_food": translated_food,
                "original_error": str(e)
            }
        )

