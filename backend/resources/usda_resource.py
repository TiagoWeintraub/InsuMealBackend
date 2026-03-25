import os
import logging
import re
import unicodedata
from dotenv import load_dotenv
import requests
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
    "mayonesa": "mayonnaise",
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
    "mayonesa": "mayonnaise",
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

            brand_owner = str(item.get("brandOwner", "") or "").strip()
            if not brand_owner:
                score += 22.0
            else:
                score -= 18.0

            data_type = str(item.get("dataType", "")).lower()
            if "branded" in data_type:
                score -= 25.0
            if any(x in data_type for x in ("foundation", "survey", "sr legacy", "legacy")):
                score += 10.0

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

        mapped = SPANISH_TO_ENGLISH_FOOD_MAP.get(normalized)
        if mapped and mapped not in candidates:
            candidates.append(mapped)

        if normalized and normalized not in candidates:
            candidates.append(normalized)

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
    def _is_branded_item(item: dict) -> bool:
        brand_owner = str(item.get("brandOwner", "") or "").strip()
        data_type = str(item.get("dataType", "") or "").lower()
        return bool(brand_owner) or "branded" in data_type

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
            foods = [item for item in foods if not self._is_branded_item(item)]
            if not foods:
                logger.warning(f"USDA sin resultados no-branded para query='{query}'")
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

        # Fallback por ingrediente: probar Edamam (sin usar estimación inventada).
        edamam_fallback = self._fallback_edamam(food_name)
        if edamam_fallback is not None:
            return edamam_fallback

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
                try:
                    usda_food_data = self.get_food_by_name(normalized_food)
                except HTTPException as lookup_exc:
                    if lookup_exc.status_code == 404:
                        logger.warning(
                            f"Ingrediente omitido por falta de match en USDA/Edamam: '{normalized_food}'"
                        )
                        continue
                    raise
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