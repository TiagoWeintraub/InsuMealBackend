import os
import logging
import re
import unicodedata
import json
from dotenv import load_dotenv
import requests
import google.generativeai as genai
from sqlmodel import Session, select
from fastapi import HTTPException
from resources.ingredient_resource import IngredientResource
from resources.edamam_resource import EdamamResource
from models.user import User
from schemas.ingredient_schema import IngredientCreate
from models.ingredient import Ingredient
from models.meal_plate import MealPlate
from resources.meal_plate_ingredient_resource import MealPlateIngredientResource
from schemas.meal_plate_ingredient_schema import MealPlateIngredientUpdate
from models.meal_plate_ingredient import MealPlateIngredient
from utils.suppress_output import safe_library_call

# Configurar logger específico para este módulo
logger = logging.getLogger(__name__)

load_dotenv()

SPANISH_TO_ENGLISH_FOOD_MAP = {
    "tomate": "tomato",
    "lechuga": "lettuce",
    "cebolla": "onion",
    "cebolla caramelizada": "caramelized onion",
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


class UsdaResource:
    def __init__(self, session: Session, current_user: User = None):
        self.current_user = current_user
        self.session = session
        self.app_key = os.getenv("USDA_API_KEY")
        self.data_type = os.getenv("USDA_DATA_TYPE", "SR Legacy")
        self.page_size = 1
        if not self.app_key:
            raise ValueError("USDA_API_KEY no está definido en el .env")
        self.base_url = os.getenv("USDA_URL", "https://api.nal.usda.gov/fdc/v1/foods/search")
        self.base_url = self.base_url.rstrip("?")

    @staticmethod
    def _normalize_food_name(food_name: str) -> str:
        text = (food_name or "").strip().lower()
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-z0-9\s\-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _extract_carbs(food_item: dict) -> float:
        carbs = next(
            (
                nutrient.get("value")
                for nutrient in food_item.get("foodNutrients", [])
                if nutrient.get("nutrientId") == 1005
                or nutrient.get("nutrientNumber") == "205"
            ),
            0.0,
        )
        return float(carbs or 0.0)

    def _pick_best_food_match(self, query: str, foods: list[dict]) -> dict | None:
        """
        Selección robusta y compacta:
        - Prioriza match exacto/singular-plural.
        - Favorece descripciones cortas y "limpias".
        - Penaliza descripciones ruidosas (includes, flavor, oil, etc.).
        """
        normalized_query = self._normalize_food_name(query)
        if not foods:
            return None

        query_singular = normalized_query.rstrip("s")
        query_tokens = set(normalized_query.split())
        noisy_tokens = {
            "includes",
            "flavor",
            "flavored",
            "style",
            "with",
            "and",
            "oil",
            "sauce",
            "dressing",
            "mix",
            "powder",
            "seasoning",
            "sweetened",
        }

        def score_item(item: dict) -> tuple[float, str]:
            description_raw = str(item.get("description", "") or "")
            description = self._normalize_food_name(description_raw)
            if not description:
                return (-10_000.0, description)

            desc_singular = description.rstrip("s")
            desc_tokens = set(description.split())
            overlap = len(query_tokens.intersection(desc_tokens))
            union_size = max(1, len(query_tokens.union(desc_tokens)))
            jaccard = overlap / union_size

            score = 0.0
            if description == normalized_query:
                score += 120.0
            if desc_singular == query_singular:
                score += 80.0
            if description.startswith(normalized_query):
                score += 25.0
            if normalized_query in description:
                score += 18.0

            score += jaccard * 40.0
            score -= max(0, len(desc_tokens) - len(query_tokens)) * 2.5
            score -= sum(1 for token in desc_tokens if token in noisy_tokens) * 10.0

            if not item.get("brandOwner"):
                score += 5.0

            data_type = str(item.get("dataType", "")).lower()
            if any(x in data_type for x in ("foundation", "survey", "sr legacy")):
                score += 4.0

            return (score, description)

        ranked: list[tuple[float, str, dict]] = []
        for item in foods:
            score, description = score_item(item)
            ranked.append((score, description, item))

        ranked.sort(key=lambda x: x[0], reverse=True)
        best_score, best_desc, best_item = ranked[0]
        logger.info(
            f"USDA best_match query='{normalized_query}' picked='{best_desc}' score={best_score:.2f}"
        )
        if len(ranked) > 1:
            runner_up = ", ".join([f"{desc}:{score:.2f}" for score, desc, _ in ranked[1:3]])
            logger.debug(f"USDA alternativas query='{normalized_query}': {runner_up}")
        return best_item

    def _build_query_candidates(self, food_name: str) -> list[str]:
        normalized = self._normalize_food_name(food_name)
        candidates: list[str] = []
        if normalized:
            candidates.append(normalized)

        mapped = SPANISH_TO_ENGLISH_FOOD_MAP.get(normalized)
        if mapped and mapped not in candidates:
            candidates.append(mapped)

        translated_tokens = [WORD_TO_ENGLISH_MAP.get(token, token) for token in normalized.split()]
        token_based = self._normalize_food_name(" ".join(translated_tokens))
        if token_based == "onion caramelized":
            token_based = "caramelized onion"
        if token_based and token_based not in candidates:
            candidates.append(token_based)

        if " " in normalized:
            primary_noun = normalized.split()[0]
            mapped_primary = WORD_TO_ENGLISH_MAP.get(primary_noun)
            if mapped_primary and mapped_primary not in candidates:
                candidates.append(mapped_primary)

        # Sinónimos puntuales de alta frecuencia en fotos de comida.
        if normalized == "guacamole":
            for synonym in ("avocado dip", "avocado"):
                if synonym not in candidates:
                    candidates.append(synonym)

        return candidates or [food_name]

    @staticmethod
    def _extract_first_json_object(text: str) -> dict | None:
        raw = (text or "").strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _fallback_edamam(self, food_name: str) -> dict | None:
        """
        Fallback por ingrediente: usa Edamam solo si está configurado.
        """
        try:
            edamam = EdamamResource(self.session, self.current_user)
            data = edamam.post_food_by_natural_language(food_name, grams=100.0)
            carbs = float(data.get("carbs", 0.0) or 0.0)
            resolved_name = self._normalize_food_name(str(data.get("food_name") or food_name))
            logger.info(
                f"Fallback Edamam exitoso para '{food_name}' -> '{resolved_name}' carbs={carbs}"
            )
            return {
                "name": resolved_name,
                "carbs": carbs,
                "unit": "G",
            }
        except Exception as exc:
            logger.warning(f"Fallback Edamam no disponible para '{food_name}': {exc}")
            return None

    def _fallback_gemini(self, food_name: str) -> dict | None:
        """
        Último fallback por ingrediente: estimar carbs/100g con Gemini.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("Fallback Gemini omitido: GEMINI_API_KEY no configurado")
            return None

        model_name = os.getenv("GEMINI_NUTRITION_FALLBACK_MODEL", "gemini-2.5-flash")
        prompt = f"""
You are a nutrition estimation assistant.
Estimate total carbohydrates per 100 grams for this ingredient: "{food_name}".
Return ONLY valid JSON with this exact shape:
{{"name":"<normalized ingredient>", "carbs_per_100g": <number>}}
Rules:
- carbs_per_100g must be a non-negative number.
- name should be concise and in English.
"""
        try:
            safe_library_call(genai.configure, api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = safe_library_call(model.generate_content, prompt)
            parsed = self._extract_first_json_object(getattr(response, "text", "") or "")
            if not parsed:
                logger.warning(f"Fallback Gemini devolvió JSON inválido para '{food_name}'")
                return None

            resolved_name = self._normalize_food_name(str(parsed.get("name") or food_name))
            carbs = float(parsed.get("carbs_per_100g", 0.0) or 0.0)
            if carbs < 0:
                carbs = 0.0

            logger.info(
                f"Fallback Gemini exitoso para '{food_name}' -> '{resolved_name}' carbs={carbs}"
            )
            return {
                "name": resolved_name,
                "carbs": carbs,
                "unit": "G",
            }
        except Exception as exc:
            logger.warning(f"Fallback Gemini no disponible para '{food_name}': {exc}")
            return None

    def get_food_by_name(self, food_name: str) -> dict:
        query_candidates = self._build_query_candidates(food_name)
        logger.info(
            f"Consultando USDA para '{food_name}' con candidatos: {query_candidates}"
        )

        last_status = None
        for query in query_candidates:
            params = {
                "api_key": self.app_key,
                "query": query,
                "dataType": self.data_type,
                "pageSize": 10,
            }
            response = requests.get(self.base_url, params=params, timeout=15)
            last_status = response.status_code

            if response.status_code != 200:
                logger.error(
                    f"Error USDA para query='{query}': {response.status_code} - {response.text}"
                )
                if response.status_code == 429:
                    raise HTTPException(
                        status_code=429,
                        detail="USDA rate limit alcanzado. Intenta nuevamente en unos segundos.",
                    )
                continue

            food_data = response.json()
            foods = food_data.get("foods") or []
            if not foods:
                logger.warning(f"USDA sin resultados para query='{query}'")
                continue

            best_match = self._pick_best_food_match(query, foods)
            if not best_match:
                logger.warning(f"USDA sin best_match para query='{query}'")
                continue

            carbs = self._extract_carbs(best_match)
            carbsUnit = next(
                (
                    nutrient.get("unitName")
                    for nutrient in best_match.get("foodNutrients", [])
                    if nutrient.get("nutrientId") == 1005
                    or nutrient.get("nutrientNumber") == "205"
                ),
                "G",
            )
            resolved_name = self._normalize_food_name(str(best_match.get("description") or query))
            logger.info(
                f"USDA match query='{query}' resolved_name='{resolved_name}' carbs={carbs}"
            )
            return {
                "name": resolved_name,
                "carbs": float(carbs or 0.0),
                "unit": carbsUnit,
            }

        logger.warning(
            f"No se encontraron resultados en USDA para '{food_name}'. "
            f"Candidatos probados: {query_candidates}. Último status={last_status}"
        )

        # Fallback por ingrediente (sin romper todo el análisis por un ítem).
        edamam_fallback = self._fallback_edamam(food_name)
        if edamam_fallback is not None:
            return edamam_fallback

        gemini_fallback = self._fallback_gemini(food_name)
        if gemini_fallback is not None:
            return gemini_fallback

        raise HTTPException(
            status_code=404,
            detail={
                "code": "ingredient_not_found",
                "message": "No se encontró el alimento en USDA.",
                "food": food_name,
                "queries_attempted": query_candidates,
            },
        )

    def orquest(self, food_dic, meal_plate: MealPlate = None) -> MealPlate:
        logger.info(
            f"Iniciando procesamiento nutricional (USDA) para {len(food_dic) if isinstance(food_dic, dict) else 'datos'} alimentos"
        )
        if not isinstance(food_dic, dict):
            raise HTTPException(status_code=400, detail="Formato inválido para food_dic")

        for key in food_dic.keys():
            normalized_food = self._normalize_food_name(key)
            grams = food_dic[key]
            ingredient_resource = IngredientResource(self.session)

            try:
                existing_ingredient = ingredient_resource.get_by_name(normalized_food)
                carbs_per_hundred = existing_ingredient.carbsPerHundredGrams
                ingredient_id = existing_ingredient.id
                logger.debug(f"Ingrediente '{normalized_food}' encontrado en BD")
            except HTTPException as e:
                if e.status_code != 404:
                    raise e

                logger.info(f"Consultando USDA para nuevo ingrediente: '{normalized_food}'")
                usda_food_data = self.get_food_by_name(normalized_food)
                normalized_api_food_name = self._normalize_food_name(usda_food_data.get("name", normalized_food))
                carbs_per_hundred = usda_food_data["carbs"]
                self.create_ingredient(meal_plate.id, normalized_api_food_name, carbs_per_hundred)
                new_ingredient = self.session.exec(
                    select(Ingredient).where(Ingredient.name == normalized_api_food_name)
                ).first()
                ingredient_id = new_ingredient.id
                normalized_food = normalized_api_food_name

            self.update_meal_plate_ingredient(carbs_per_hundred, grams, ingredient_id, meal_plate.id)
            logger.info(
                f"Procesado: {normalized_food} - {round((carbs_per_hundred * grams) / 100, 2)}g carbohidratos ({grams}g porción)"
            )

        logger.info("Procesamiento nutricional (USDA) completado exitosamente")
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
                logger.debug(
                    f"El ingrediente {ingredient_id} ya está asociado al MealPlate {meal_plate_id}"
                )
                return existing_ingredient
        except Exception as e:
            if isinstance(e, HTTPException) and e.status_code == 404:
                logger.debug(
                    f"Creando nueva relación MealPlateIngredient para ingrediente {ingredient_id}"
                )
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
            resource.get_one(meal_plate_id, ingredient_id)
            data = MealPlateIngredientUpdate(grams=round(grams, 2), carbs=carbs)
            resource.update(meal_plate_id, ingredient_id, data)
        except HTTPException as e:
            if e.status_code == 404:
                logger.debug(
                    f"Creando nueva relación MealPlate {meal_plate_id} - Ingredient {ingredient_id}"
                )
                self.add_ingredient_to_meal_plate(ingredient_id, meal_plate_id)
                data = MealPlateIngredientUpdate(grams=round(grams, 2), carbs=carbs)
                resource.update(meal_plate_id, ingredient_id, data)
            else:
                logger.error(f"Error inesperado al actualizar MealPlateIngredient: {e}")
                raise e
        return carbs