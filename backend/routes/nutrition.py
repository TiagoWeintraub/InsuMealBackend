import os
import json
import re
import logging
import unicodedata
import math

import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from auth.dependencies import get_current_user
from database import get_session
from models.meal_plate import MealPlate
from models.user import User
from resources.ingredient_resource import IngredientResource
from resources.nutrition_resource import NutritionResource
from utils.suppress_output import safe_library_call

logger = logging.getLogger(__name__)

SPANISH_TO_ENGLISH_FOOD_MAP = {
    "tomate": "tomato",
    "lechuga": "lettuce",
    "cebolla": "onion",
    "cebolla caramelizada": "caramelized onions",
    "zanahoria": "carrot",
    "papa": "potato",
    "patata": "potato",
    "queso": "cheese",
    "queso mozzarella": "mozzarella cheese",
    "jamon": "ham",
    "pollo": "chicken",
    "carne": "beef",
    "pan": "bread",
    "arroz": "rice",
    "galleta": "cookie",
}

WORD_TO_ENGLISH_MAP = {
    "cebolla": "onion",
    "caramelizada": "caramelized",
    "tomate": "tomato",
    "lechuga": "lettuce",
    "queso": "cheese",
    "jamon": "ham",
    "pollo": "chicken",
    "carne": "beef",
    "pan": "bread",
    "arroz": "rice",
    "galleta": "cookie",
}

SWEET_INGREDIENT_KEYWORDS = (
    "cookie",
    "galleta",
    "candy",
    "cake",
    "brownie",
    "ice cream",
    "chocolate",
    "caramelo",
    "dessert",
    "postre",
)

DESSERT_MEAL_KEYWORDS = (
    "dessert",
    "postre",
    "sweet",
    "cake",
    "helado",
    "ice cream",
    "brownie",
    "flan",
)


class SingleFoodRequest(BaseModel):
    food: str


def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no está definido en el .env")
    safe_library_call(genai.configure, api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash-lite")


def estimate_food_portions_with_gemini(food_list: list, meal_plate_name: str) -> dict:
    try:
        model = setup_gemini()
        foods_text = ", ".join(food_list)
        prompt = f"""
Estimate grams for the following ingredient(s) in this dish.
Dish: {meal_plate_name}
Ingredients: {foods_text}
Return only a valid JSON object where each key is ingredient name and each value is integer grams.
"""
        response = safe_library_call(model.generate_content, prompt)
        clean_response = clean_gemini_response(response.text)
        estimated_portions = json.loads(clean_response)
        if isinstance(estimated_portions, dict):
            return estimated_portions
        return {food: 100 for food in food_list}
    except Exception:
        return {food: 100 for food in food_list}


def normalize_food_name(food_name: str) -> str:
    text = (food_name or "").strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def translate_food_to_english(food_name: str, meal_plate_name: str) -> str:
    """
    Similar a la lógica histórica: intenta llevar el alimento a un nombre corto en inglés.
    Si falla Gemini, devuelve el nombre normalizado original.
    """
    normalized = normalize_food_name(food_name)
    if not normalized:
        return ""

    mapped = SPANISH_TO_ENGLISH_FOOD_MAP.get(normalized)
    if mapped:
        logger.info(f"Traducción por diccionario local: '{normalized}' -> '{mapped}'")
        return mapped

    translated_tokens = [WORD_TO_ENGLISH_MAP.get(token, token) for token in normalized.split()]
    token_based_translation = normalize_food_name(" ".join(translated_tokens))
    if token_based_translation and token_based_translation != normalized:
        # USDA suele resolver mejor "caramelized onion" que "onion caramelized"
        if token_based_translation == "onion caramelized":
            token_based_translation = "caramelized onion"
        logger.info(
            f"Traducción por tokens: '{normalized}' -> '{token_based_translation}'"
        )
        return token_based_translation

    try:
        model = setup_gemini()
        prompt = f"""
Translate this food ingredient name to concise English for nutrition database lookup.
Dish context: {meal_plate_name}
Input ingredient: {normalized}
Return only valid JSON with shape: {{"food_en":"..."}}
"""
        response = safe_library_call(model.generate_content, prompt)
        clean_response = clean_gemini_response(response.text or "")
        parsed = json.loads(clean_response)
        translated = normalize_food_name(str(parsed.get("food_en", "")))
        if translated:
            logger.info(f"Traducción con Gemini: '{normalized}' -> '{translated}'")
            return translated
        logger.warning(
            f"Gemini no devolvió traducción usable para '{normalized}'. Se usa original normalizado."
        )
        return normalized
    except Exception as exc:
        logger.warning(
            f"No se pudo traducir '{normalized}' con Gemini ({exc}). Se usa original normalizado."
        )
        return normalized


def clean_gemini_response(response_text: str) -> str:
    json_pattern = r"\{[\s\S]*\}"
    match = re.search(json_pattern, (response_text or "").strip())
    if match:
        return match.group(0)
    return "{}"


def is_food_compatible_with_meal_context(food_name: str, meal_type: str) -> bool:
    normalized_food = normalize_food_name(food_name)
    normalized_meal_type = normalize_food_name(meal_type)

    is_sweet_ingredient = any(keyword in normalized_food for keyword in SWEET_INGREDIENT_KEYWORDS)
    is_dessert_meal = any(keyword in normalized_meal_type for keyword in DESSERT_MEAL_KEYWORDS)

    if is_sweet_ingredient and not is_dessert_meal:
        return False
    return True


router = APIRouter(prefix="/nutrition")


@router.post("/add/food/{meal_plate_id}")
async def process_single_food(
    meal_plate_id: int,
    request: SingleFoodRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    food_name = (request.food or "").strip()
    if not food_name:
        raise HTTPException(status_code=400, detail="El nombre del alimento no puede estar vacío")

    normalized_input = normalize_food_name(food_name)
    translated_food = normalized_input

    meal_plate = session.get(MealPlate, meal_plate_id)
    if not meal_plate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MealPlate no encontrado")

    translated_food = translate_food_to_english(normalized_input, meal_plate.type or "")
    if not translated_food:
        translated_food = normalized_input

    logger.info(
        f"Procesando alimento manual. original='{food_name}' normalized='{normalized_input}' translated='{translated_food}'"
    )

    if not is_food_compatible_with_meal_context(translated_food, meal_plate.type or ""):
        logger.info(
            f"Ingrediente fuera de contexto. food='{translated_food}' meal_type='{meal_plate.type}'"
        )
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ingredient_out_of_context",
                "message": (
                    f"El alimento '{food_name}' no parece corresponder al contexto del plato "
                    f"'{meal_plate.type}'."
                ),
                "original_food": food_name,
                "translated_food": translated_food,
                "meal_type": meal_plate.type,
            },
        )

    ingredient_resource = IngredientResource(session)
    candidate_names = [name for name in [translated_food, normalized_input] if name]
    try:
        meal_plate_details = ingredient_resource.read_ingredients_by_meal_plate(meal_plate_id)
        existing_ingredient_ids = [ing["id"] for ing in meal_plate_details["ingredients"]]
        for candidate in candidate_names:
            try:
                existing_ingredient = ingredient_resource.get_by_name(candidate)
            except HTTPException as inner_exc:
                if inner_exc.status_code == 404:
                    continue
                raise

            if existing_ingredient.id in existing_ingredient_ids:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error_type": "FOOD_ALREADY_EXISTS",
                        "message": f"El alimento '{food_name}' ya está en este plato",
                        "original_food": food_name,
                        "translated_food": translated_food,
                        "ingredient_id": existing_ingredient.id,
                        "suggestion": "El alimento ya fue agregado previamente a este plato",
                    },
                )
    except HTTPException as e:
        if e.status_code not in (404, 409):
            raise
        if e.status_code == 409:
            raise

    estimated_portions = estimate_food_portions_with_gemini([translated_food], meal_plate.type)
    raw_estimated_weight = estimated_portions.get(translated_food, 100)
    try:
        estimated_weight = float(raw_estimated_weight)
    except (TypeError, ValueError):
        estimated_weight = 100.0

    if not math.isfinite(estimated_weight) or estimated_weight <= 0:
        logger.warning(
            f"Peso estimado inválido para '{translated_food}': {raw_estimated_weight}. Se usa 100g."
        )
        estimated_weight = 100.0

    food_with_weight = {translated_food: estimated_weight}

    nutrition_resource = NutritionResource(session, current_user)
    nutrition_resource.orquest(food_with_weight, meal_plate)

    meal_plate_details = ingredient_resource.read_ingredients_by_meal_plate(meal_plate_id)
    return {
        "message": "Alimento procesado exitosamente",
        "original_food": food_name,
        "translated_food": translated_food,
        "estimated_weight": estimated_weight,
        "meal_plate_details": meal_plate_details,
    }
