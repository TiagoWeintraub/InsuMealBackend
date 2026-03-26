import os
import json
import re
import logging
import unicodedata
import math
from datetime import datetime, timezone

import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from auth.dependencies import get_current_user
from database import get_session
from models.meal_plate import MealPlate
from models.user import User
from models.usage import Usage
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
    "mayonesa": "mayonnaise",
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
    "mayonesa": "mayonnaise",
    "galleta": "cookie",
}

PORTION_MODEL_FALLBACK_ORDER = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
]

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


def _register_usage_from_gemini_response(
    session: Session,
    user_id: int,
    response,
    model_name: str,
) -> None:
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    total_tokens = int(getattr(usage, "total_token_count", 0) or 0)

    usage_record = Usage(
        user_id=user_id,
        provider="google",
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        created_at=datetime.now(timezone.utc),
    )
    session.add(usage_record)
    session.commit()


def estimate_food_portions_with_gemini(
    food_list: list,
    meal_plate_name: str,
    session: Session,
    user_id: int,
) -> dict | None:
    foods_text = ", ".join(food_list)
    prompt = f"""
Estimate grams for the following ingredient(s) in this dish.
Dish: {meal_plate_name}
Ingredients: {foods_text}
Return only a valid JSON object where each key is ingredient name and each value is integer grams.
"""
    last_error = None

    for model_name in PORTION_MODEL_FALLBACK_ORDER:
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY no está definido en el .env")
            safe_library_call(genai.configure, api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = safe_library_call(model.generate_content, prompt)
            _register_usage_from_gemini_response(
                session=session,
                user_id=user_id,
                response=response,
                model_name=model_name,
            )
            clean_response = clean_gemini_response(response.text)
            estimated_portions = json.loads(clean_response)
            if isinstance(estimated_portions, dict):
                logger.info(f"Estimación de porción resuelta con modelo: {model_name}")
                return estimated_portions
        except Exception as exc:
            last_error = exc
            logger.warning(
                f"Estimación de porción falló con modelo {model_name}: {exc}"
            )
            continue

    logger.warning(f"No se pudo estimar porción con Gemini. Último error: {last_error}")
    return None


def infer_food_and_portion_with_gemini(
    original_food: str,
    translated_food: str,
    meal_plate_name: str,
    session: Session,
    user_id: int,
) -> tuple[str | None, float | None]:
    prompt = f"""
You are helping a diabetes meal app.
Given one ingredient and a dish context, return a canonical English ingredient name and grams.

Dish: {meal_plate_name}
User ingredient (original): {original_food}
Current normalized translation: {translated_food}

Rules:
- Return ONLY valid JSON with shape: {{"food_en":"...", "grams": number}}
- food_en must be a generic ingredient name (no brands).
- Keep same ingredient meaning (do not replace with a different ingredient).
- grams must be a positive number, realistic for ONE portion in the given dish context.
"""
    last_error = None

    for model_name in PORTION_MODEL_FALLBACK_ORDER:
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY no está definido en el .env")
            safe_library_call(genai.configure, api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = safe_library_call(model.generate_content, prompt)
            _register_usage_from_gemini_response(
                session=session,
                user_id=user_id,
                response=response,
                model_name=model_name,
            )

            parsed = json.loads(clean_gemini_response(response.text or ""))
            if not isinstance(parsed, dict):
                continue

            food_en = normalize_food_name(str(parsed.get("food_en") or ""))
            grams_raw = parsed.get("grams")
            grams = None
            try:
                grams = float(grams_raw)
            except (TypeError, ValueError):
                grams = None

            if grams is not None and (not math.isfinite(grams) or grams <= 0):
                grams = None

            return (food_en or None, grams)
        except Exception as exc:
            last_error = exc
            logger.warning(
                f"Inferencia food+grams falló con modelo {model_name}: {exc}"
            )
            continue

    logger.warning(f"No se pudo inferir food+grams con Gemini. Último error: {last_error}")
    return (None, None)


def _estimate_portion_with_heuristics(food_name: str, meal_plate_name: str) -> float | None:
    normalized_food = normalize_food_name(food_name)
    normalized_meal = normalize_food_name(meal_plate_name)

    condiment_keywords = ("ketchup", "mayonnaise", "mustard", "barbecue", "salsa", "soy sauce")
    sauce_keywords = ("sauce", "dressing", "dip")

    if any(keyword in normalized_food for keyword in condiment_keywords):
        return 8.0
    if any(keyword in normalized_food for keyword in sauce_keywords):
        return 15.0
    if "cheddar cheese" in normalized_food or "mozzarella cheese" in normalized_food:
        return 30.0

    if "hamburger" in normalized_meal or "burger" in normalized_meal:
        if "onion" in normalized_food or "pickle" in normalized_food or "tomato" in normalized_food:
            return 15.0
        if "lettuce" in normalized_food:
            return 10.0

    return None


def _extract_estimated_weight(estimated_portions: dict, candidates: list[str]) -> float | None:
    normalized_candidates = [normalize_food_name(candidate) for candidate in candidates if candidate]
    for key, value in estimated_portions.items():
        normalized_key = normalize_food_name(str(key))
        if normalized_key in normalized_candidates:
            try:
                grams = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(grams) and grams > 0:
                return grams
    return None


def normalize_food_name(food_name: str) -> str:
    text = (food_name or "").strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def translate_food_to_english(
    food_name: str,
    meal_plate_name: str,
    session: Session,
    user_id: int,
) -> str:
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
        _register_usage_from_gemini_response(
            session=session,
            user_id=user_id,
            response=response,
            model_name="gemini-2.0-flash-lite",
        )
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

    translated_food = translate_food_to_english(
        normalized_input,
        meal_plate.type or "",
        session=session,
        user_id=current_user.id,
    )
    if not translated_food:
        translated_food = normalized_input

    logger.info(
        f"Procesando alimento manual. original='{food_name}' normalized='{normalized_input}' translated='{translated_food}'"
    )

    inferred_food, inferred_grams = infer_food_and_portion_with_gemini(
        original_food=normalized_input,
        translated_food=translated_food,
        meal_plate_name=meal_plate.type or "",
        session=session,
        user_id=current_user.id,
    )
    if inferred_food:
        logger.info(
            f"Inferencia canónica de ingrediente aplicada: '{translated_food}' -> '{inferred_food}'"
        )
        translated_food = inferred_food

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

    estimated_weight: float | None = inferred_grams

    if estimated_weight is None:
        estimated_portions = estimate_food_portions_with_gemini(
            [translated_food],
            meal_plate.type or "",
            session=session,
            user_id=current_user.id,
        )
        if isinstance(estimated_portions, dict):
            estimated_weight = _extract_estimated_weight(
                estimated_portions,
                [translated_food, normalized_input],
            )

    if estimated_weight is None:
        estimated_weight = _estimate_portion_with_heuristics(translated_food, meal_plate.type or "")
        if estimated_weight is not None:
            logger.info(
                f"Porción estimada con heurística para '{translated_food}' en '{meal_plate.type}': {estimated_weight}g"
            )

    if estimated_weight is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "portion_estimation_failed",
                "message": (
                    f"No se pudo estimar los gramos para '{food_name}' de forma confiable. "
                    "Intenta con otro alimento o una descripción más específica."
                ),
                "original_food": food_name,
                "translated_food": translated_food,
                "meal_type": meal_plate.type,
            },
        )

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
