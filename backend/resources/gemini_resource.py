import io
import os
from PIL import Image, ImageOps
from PIL.Image import Resampling
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Union
import re
from sqlmodel import Session
from resources.meal_plate_resource import MealPlateResource
from models.user import User
from fastapi import HTTPException
from models.food_history import FoodHistory
import imghdr
from sqlmodel import select
from resources.edamam_resource import EdamamResource
from resources.nutritionix_resource import NutritionixResource
from models.meal_plate import MealPlate


load_dotenv()

class GeminiResource:
    def __init__(self, session: Session):
        self.session = session
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está definido en el .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")

    def create_meal_plate(self, imagen: bytes, mime_type: str, food_history_id: int, food_text_dic) -> None:
        meal_plate_resource = MealPlateResource(self.session)
        response = meal_plate_resource.create(
            picture=imagen,
            mime_type=mime_type,
            type= str(list(food_text_dic.keys())[0]).lower(),
            food_history_id=food_history_id,
            totalCarbs=0.0,
            dosis=0.0,
        )
        return response

    def analyze_image(self, image_data: bytes, current_user: User) -> Union[str, dict]:
        try:
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
            print("Enviando imagen y prompt a Gemini")
            response = self.model.generate_content([image, prompt])
            print("Respuesta de Gemini recibida")
            
            food_text_dic = self.clean_data(response.text)
            print("El diccionario de alimentos ha sido limpiado y es: ", food_text_dic)

            # Se busca el FoodHistory del usuario
            food_history = self.session.exec(
                select(FoodHistory).where(FoodHistory.user_id == current_user.id)
            ).first()
            
            if not food_history:
                raise HTTPException(status_code=404, detail="No se encontró historial de comidas para este usuario.")

            # Se busca el último MealPlate del usuario
            meal_plate_id = self.create_meal_plate(imagen, mime_type, food_history.id, food_text_dic)


            # Al recurso call edamam se le envia el diccionario de alimentos sin el primer elemento clave-valor
            edamam_dic = {k: v for k, v in food_text_dic.items() if k != list(food_text_dic.keys())[0]}
            print("El diccionario de alimentos que se le envía a Edamam es: ", edamam_dic)


            
            self.call_nutritional_api_resource(edamam_dic, meal_plate_id ,current_user)

            return food_text_dic

        except HTTPException as http_exc:
            print(f"Error HTTP: {http_exc.detail}")
            raise http_exc
        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

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
            print("Diccionario de alimentos extraído")
            return food_dict
        else:
            print("No se encontró el diccionario en el texto.")
    
    def reduce_image_weight(self, image_data: bytes, target_max_kb=500) -> bytes:
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
            print("La imagen no ha cambiado de peso y sus dimensiones son las mismas.")
        else:
            print(f"Peso final: {final_size_kb:.2f} KB con calidad {quality}")
            print(f"Dimensiones finales: {image.size}")
        print("Imagen comprimida")
        return compressed_data

    def call_nutritional_api_resource(self, food_dic, meal_plate_id,current_user: User) -> None:

        # edamam_resource = EdamamResource(self.session, current_user)
        # edamam_resource.orquest(food_dic)
        
        nutritionix_resource = NutritionixResource(self.session, current_user)
        nutritionix_resource.orquest(food_dic,meal_plate_id)
        print("Se ha llamado a EdamamResource")