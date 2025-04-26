import os
import io
from PIL import Image, ImageOps
from PIL.Image import Resampling
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Union
import re
from sqlmodel import Session
from schemas.meal_plate_schema import MealPlateCreate
from resources.meal_plate_resource import MealPlateResource
from schemas.food_history_schema import FoodHistoryCreate
from resources.food_history_resource import FoodHistoryResource
from models.user import User

load_dotenv()

class GeminiResource:
    def __init__(self, session: Session):
        self.session = session
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está definido en el .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")

    def analyze_image(self, image_data: bytes, current_user: User) -> Union[str, dict]:
        try:
            # Reducimos el peso de la imagen 
            imagen = self.reduce_image_weight(image_data)
            # Convertimos la imagen a un objeto de tipo Image
            image = Image.open(io.BytesIO(imagen))

            # Prompt detallado in-context learning
            with open("in-context-learning/prompt.txt", "r") as f:
                prompt = f.read()

            # Enviar imagen y prompt
            response = self.model.generate_content([image, prompt])
            
            food_text_dic = self.clean_data(response.text)
            
            # Se crea el meal_plate sin asignar un valor genérico en "type" ni la fecha,
            # de modo que la BD asigne automáticamente la fecha de creación.
            # También se asigna el food_history del usuario actual.
            meal_plate_resource = MealPlateResource(self.session)
            meal_plate = meal_plate_resource.create(
                MealPlateCreate(
                    picture=image_data,
                    type="",  # Se deja vacío para no asignar un valor genérico.
                    food_history_id=current_user.food_history.id
                )
            )
            
            return food_text_dic

        except Exception as e:
            return {"error": str(e)}

    def clean_data(self, data: str) -> dict:
        match = re.search(r"food\s*=\s*({.*?})", data, re.DOTALL)
        if match:
            dict_str = match.group(1)
            food_dict = {}
            items = dict_str[1:-1].split(",")  # Eliminar llaves y separar
            for item in items:
                key_value = item.split(":")
                key = key_value[0].strip().strip("'\"")
                value = key_value[1].strip()
                try:
                    value = int(value)
                except ValueError:
                    pass
                food_dict[key] = value
            return food_dict
        else:
            print("No se encontró el diccionario en el texto.")
    
    def reduce_image_weight(self, image_data: bytes, target_max_kb=500) -> bytes:
        target_max_bytes = target_max_kb * 1024
        image = Image.open(io.BytesIO(image_data))
        image = ImageOps.exif_transpose(image)
        print(f"Peso original en MB: {len(image_data) / (1024 * 1024):.2f} MB")
        print(f"Dimensiones originales: {image.size}")
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
            print("La imagen no ha cambiado de peso y sus dimensiones son las mismas.")
        else:
            print(f"Peso final: {final_size_kb:.2f} KB con calidad {quality}")
            print(f"Dimensiones finales: {image.size}")
        return compressed_data