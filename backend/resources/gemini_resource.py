import io
import os
import sys
import logging
from datetime import datetime, timezone
from contextlib import redirect_stdout, redirect_stderr
from PIL import Image, ImageOps
from PIL.Image import Resampling
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Union
import re
import json
from sqlmodel import Session
from resources.meal_plate_resource import MealPlateResource
from models.user import User
from fastapi import HTTPException
from models.food_history import FoodHistory
from models.usage import Usage
import imghdr
from sqlmodel import select
from resources.edamam_resource import EdamamResource
from models.meal_plate import MealPlate
import warnings

# Importar configuración para suprimir salidas
from utils.suppress_output import safe_library_call

# Configurar logger específico para este módulo
logger = logging.getLogger(__name__)

load_dotenv()


def _meal_image_generation_config() -> genai.GenerationConfig:
    """
    Una sola petición a Gemini: forzar salida JSON válida (sin markdown ni texto extra).

    Formato del JSON (igual que antes):
      - Rechazo: {"analysis_rejected": true, "reject_reason": "...", "user_message": "..."}
      - Comida:  {"Pizza": 1, "pizza dough": 350, ...}

    Nota: Un response_schema con anyOf (rechazo vs. claves libres de plato) no convierte bien
    en el SDK google-generativeai; response_mime_type="application/json" sí garantiza JSON válido.
    """
    try:
        temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
    except ValueError:
        temperature = 0.2
    return genai.GenerationConfig(
        response_mime_type="application/json",
        temperature=temperature,
    )


def _normalize_meal_numeric_values(data: dict) -> dict:
    """Convierte valores del diccionario de comida a float (gramos / unidades)."""
    out: dict = {}
    for key, val in data.items():
        if isinstance(val, bool):
            continue
        if isinstance(val, (int, float)):
            out[key] = float(val)
            continue
        if isinstance(val, str):
            try:
                s = val.strip()
                out[key] = float(s) if "." in s else float(int(s))
            except ValueError:
                pass
    return out


class GeminiResource:
    def __init__(self, session: Session):
        self.session = session
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está definido en el .env")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.provider = "google"
        self.model_name = model_name

        # Configurar de forma segura
        safe_library_call(genai.configure, api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def create_meal_plate(self, imagen: bytes, mime_type: str, food_history_id: int, food_text_dic) -> None:
        meal_plate_resource = MealPlateResource(self.session)
        
        meal_type = 'unknown'
        if food_text_dic and len(food_text_dic.keys()) > 0:
            meal_type = str(list(food_text_dic.keys())[0]).lower()
        
        response = meal_plate_resource.create(
            picture=imagen,
            mime_type=mime_type,
            type= meal_type,
            food_history_id=food_history_id,
            totalCarbs=0,
            dosis=0.0,
        )
        
        return response

    @staticmethod
    def _default_rejection_message(code: str) -> str:
        messages = {
            "no_food": "No se detecta un plato de comida en la imagen. Sube una foto de tu comida.",
            "industrial_snack": "Esta app está pensada para comidas y platos. Los caramelos u snacks industriales empaquetados no se pueden analizar aquí de forma segura para la dosis de insulina.",
            "not_a_meal": "No se puede estimar un plato con ingredientes reconocibles. Prueba con otra foto más clara.",
        }
        return messages.get(code, messages["no_food"])

    def _parse_analysis_rejection(self, text: str) -> dict | None:
        """
        Respaldo: extrae rechazo si el texto no era JSON puro (modelos antiguos / markdown).
        """
        if not text or "analysis_rejected" not in text:
            return None
        cleaned = text.strip()
        if "```" in cleaned:
            fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned)
            if fence:
                cleaned = fence.group(1)
        start = cleaned.find("{")
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(cleaned)):
            c = cleaned[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    chunk = cleaned[start : i + 1]
                    try:
                        obj = json.loads(chunk)
                    except json.JSONDecodeError:
                        return None
                    if obj.get("analysis_rejected") is True:
                        return obj
                    return None
        return None

    def _parse_strict_json_response(self, raw_text: str) -> dict:
        """
        Con response_mime_type=application/json, el cuerpo suele ser un único objeto JSON.
        Si falla, intentamos rechazo embebido y luego el parser legado de diccionario de comida.
        """
        text = (raw_text or "").strip()
        if not text:
            return {}

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("JSON inválido pese a MIME JSON; probando parsers de respaldo")
            rejection = self._parse_analysis_rejection(text)
            if rejection:
                return rejection
            return self.clean_data(text)

        if not isinstance(data, dict):
            return {}

        return data

    def _interpret_analysis_dict(self, data: dict) -> tuple[str, dict]:
        """
        Decide si es rechazo o comida. Mantiene el mismo contrato que antes.

        Returns:
            ("reject", dict con reject_reason / user_message) o ("meal", dict solo plato+ingredientes).
        """
        if not data:
            return (
                "reject",
                {
                    "reject_reason": "no_food",
                    "user_message": self._default_rejection_message("no_food"),
                },
            )

        if data.get("analysis_rejected") is True:
            return ("reject", data)

        meal = {
            k: v
            for k, v in data.items()
            if k not in ("analysis_rejected", "reject_reason", "user_message")
        }
        meal = _normalize_meal_numeric_values(meal)
        return ("meal", meal)

    def analyze_image(self, image_data: bytes, current_user: User) -> Union[str, dict]:
        try:
            # Verificamos las dimensiones de la imagen y si es válida
            if not image_data or len(image_data) == 0:
                raise HTTPException(status_code=400, detail="No se ha proporcionado una imagen válida.")
            
            # Dimensiones recibidas
            logger.info(f"Imagen recibida: {len(image_data)} bytes")
            
            
            # Reducimos el peso de la imagen 
            imagen = self.reduce_image_weight(image_data)
            # Convertimos la imagen a un objeto de tipo Image
            image = Image.open(io.BytesIO(imagen))

            # Detectar automáticamente el mime_type
            detected_type = imghdr.what(None, imagen)
            mime_type = f"image/{detected_type}" if detected_type else "application/octet-stream"

            # Prompt detallado in-context learning
            with open("in-context-learning/prompt.txt", "r") as f:
                prompt = f.read()

            # Enviar imagen y prompt
            logger.info("Enviando imagen a Gemini AI para análisis")
            
            # Una sola petición: JSON estricto vía API (ver _meal_image_generation_config)
            response = safe_library_call(
                self.model.generate_content,
                [image, prompt],
                generation_config=_meal_image_generation_config(),
            )
            self._register_usage(current_user.id, response)

            logger.info("Respuesta de Gemini AI recibida exitosamente")

            parsed = self._parse_strict_json_response(response.text or "")
            kind, payload = self._interpret_analysis_dict(parsed)

            if kind == "reject":
                code = payload.get("reject_reason", "no_food")
                if code not in ("no_food", "industrial_snack", "not_a_meal"):
                    code = "no_food"
                msg = payload.get("user_message") or self._default_rejection_message(code)
                logger.info(f"Análisis rechazado por Gemini: {code}")
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": code,
                        "message": msg,
                    },
                )

            food_text_dic = payload
            logger.debug("Respuesta de Gemini procesada (JSON)")

            if not food_text_dic:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "parse_error",
                        "message": "No se pudo extraer información de los alimentos de la imagen. Por favor, intenta con otra imagen más clara.",
                    },
                )

            # Se busca el FoodHistory del usuario
            food_history = self.session.exec(
                select(FoodHistory).where(FoodHistory.user_id == current_user.id)
            ).first()
            
            if not food_history:
                raise HTTPException(status_code=404, detail="No se encontró historial de comidas para este usuario.")

            # Al recurso call nutritional_api se le envia el diccionario de alimentos sin el primer elemento clave-valor
            nutritional_api_dic = {k: v for k, v in food_text_dic.items() if k != list(food_text_dic.keys())[0]}
            logger.debug(f"Diccionario enviado a API nutricional: {nutritional_api_dic}")

            # Se crea el MealPlate solo si el diccionario de alimentos no está vacío
            if not nutritional_api_dic or len(nutritional_api_dic) == 0:
                logger.warning("No se encontraron alimentos para procesar")
                return -1
            meal_plate = self.create_meal_plate(imagen, mime_type, food_history.id, food_text_dic)
            
            logger.info(f"MealPlate creado exitosamente con ID: {meal_plate.id}")

            self.call_nutritional_api_resource(nutritional_api_dic, meal_plate, current_user)

            # Recalcular totalCarbs del plato a partir de los ingredientes
            meal_plate_resource = MealPlateResource(self.session)
            meal_plate_resource.calculate_total_carbs(meal_plate.id)

            # Asegurar que todo se guarda correctamente
            self.session.commit()
            return meal_plate.id

        except HTTPException as http_exc:
            logger.error(f"Error HTTP en análisis de imagen: {http_exc.detail}")
            self.session.rollback()  
            raise http_exc
        except Exception as e:
            logger.error(f"Error inesperado en análisis de imagen: {str(e)}")
            self.session.rollback()
            raise HTTPException(status_code=500, detail="Error interno del servidor")

    def clean_data(self, data: str) -> dict:
        logger.debug(f"Datos recibidos de Gemini: {data[:100]}...")  # Solo los primeros 100 caracteres
        
        # Intentar múltiples patrones para extraer el diccionario
        patterns = [
            r"food\s*=\s*({.*?})",  # Patrón original: food = {...}
            r"```python\s*({.*?})\s*```",  # Patrón para código Python con backticks
            r"({.*?})",  # Patrón genérico para cualquier diccionario
        ]
        
        dict_str = None
        for pattern in patterns:
            match = re.search(pattern, data, re.DOTALL)
            if match:
                dict_str = match.group(1)
                logger.debug(f"Diccionario encontrado con patrón: {pattern}")
                break
        
        if dict_str:
            food_dict = {}
            # Limpiar el string del diccionario
            dict_str = dict_str.strip()
            if dict_str.startswith('{') and dict_str.endswith('}'):
                dict_str = dict_str[1:-1]  # Eliminar llaves externas
            
            # Dividir por comas, pero cuidando las comillas
            items = []
            current_item = ""
            in_quotes = False
            quote_char = None
            
            for char in dict_str + ",":  # Añadir coma al final para procesar el último elemento
                if char in ['"', "'"] and (not in_quotes or char == quote_char):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    else:
                        in_quotes = False
                        quote_char = None
                    current_item += char
                elif char == "," and not in_quotes:
                    if current_item.strip():
                        items.append(current_item.strip())
                    current_item = ""
                else:
                    current_item += char
            
            for item in items:
                # Verificar que el item contiene ":"
                if ":" not in item:
                    print(f"Elemento mal formateado: {item} - saltando")
                    continue

                key_value = item.split(":", 1)  # Limitar a un solo split
                key = key_value[0].strip().strip("'\"")
                value = key_value[1].strip().strip(',')  # Eliminar coma al final si existe
                
                # Limpiar comillas del valor si es string
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Intentar convertir a número
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass  # Mantener como string si no se puede convertir
                
                food_dict[key] = value
            
            logger.debug(f"Diccionario de alimentos extraído: {food_dict}")
            
            # Convertir todos los values a float si son strings numéricos
            for key in food_dict:
                if isinstance(food_dict[key], str):
                    try:
                        food_dict[key] = float(food_dict[key])
                    except ValueError:
                        pass 
            return food_dict
        else:
            logger.warning("No se encontró diccionario válido en la respuesta de Gemini")
            return {}
    
    def reduce_image_weight(self, image_data: bytes, target_max_kb=500) -> bytes:
        # Solo se reduce si la dimesion de la imagen es mayor a 300x300
        if len(image_data) > 300 * 300:
            target_max_bytes = target_max_kb * 1024
            image = Image.open(io.BytesIO(image_data))
            image = ImageOps.exif_transpose(image)
            if image.mode != "RGB":
                image = image.convert("RGB")
            max_dimension = 1024  
            if max(image.size) > max_dimension:
                image.thumbnail((max_dimension, max_dimension), Resampling.LANCZOS)
            quality = 90
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality)
            while output.tell() > target_max_bytes and quality > 10:
                quality -= 5
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=quality)
            compressed_data = output.getvalue()
            final_size_kb = len(compressed_data) / 1024
            if image_data == compressed_data:
                logger.debug("La imagen no requirió compresión")
            else:
                logger.info(f"Imagen comprimida: {final_size_kb:.2f} KB (calidad {quality}), dimensiones: {image.size}")
            return compressed_data
        else:
            logger.debug("La imagen es demasiado pequeña para ser comprimida")
            return image_data
    

    def call_nutritional_api_resource(self, food_dic, meal_plate: MealPlate ,current_user: User) -> None:
        try:
            edamam_resource = EdamamResource(self.session, current_user)
            edamam_resource.orquest(food_dic, meal_plate)

            self.session.commit()

            logger.info("Información nutricional procesada exitosamente")
        except HTTPException as e:
            self.session.rollback()
            # Edamam: alimento inexistente (p. ej. Gemini inventó "laptop" en una foto que no es comida)
            if e.status_code == 404:
                logger.warning(f"Ingrediente no resuelto en API nutricional: {e.detail}")
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "ingredient_not_found",
                        "message": (
                            "No se encontró información nutricional para uno de los elementos detectados. "
                            "Si la imagen no es un plato de comida, sube una foto del plato."
                        ),
                    },
                ) from e
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error al procesar información nutricional: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error al procesar la información nutricional: {str(e)}")

    def _register_usage(self, user_id: int, response) -> None:
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        total_tokens = int(getattr(usage, "total_token_count", 0) or 0)

        usage_record = Usage(
            user_id=user_id,
            provider=self.provider,
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(usage_record)
        self.session.commit()
