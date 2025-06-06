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

    def analyze_image(self, image_data: bytes, current_user: User) -> Union[str, dict]:
        try:
            # Verificamos las dimensiones de la imagen y si es válida
            if not image_data or len(image_data) == 0:
                raise HTTPException(status_code=400, detail="No se ha proporcionado una imagen válida.")
            
            # Dimensiones recibidas
            print(f"Dimensiones de la imagen recibida: {len(image_data)} bytes")
            
            
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
            print("La respuesta de Gemini ha sido limpiada")
            
            if not food_text_dic:
                raise HTTPException(
                    status_code=422, 
                    detail="No se pudo extraer información de los alimentos de la imagen. Por favor, intenta con otra imagen más clara."
            )

            # Se busca el FoodHistory del usuario
            food_history = self.session.exec(
                select(FoodHistory).where(FoodHistory.user_id == current_user.id)
            ).first()
            
            if not food_history:
                raise HTTPException(status_code=404, detail="No se encontró historial de comidas para este usuario.")

            # Al recurso call nutritional_api se le envia el diccionario de alimentos sin el primer elemento clave-valor
            nutritional_api_dic = {k: v for k, v in food_text_dic.items() if k != list(food_text_dic.keys())[0]}
            print("El diccionario de alimentos que se le envía a nutritional_api es: ", nutritional_api_dic)

            # Se crea el MealPlate
            meal_plate = self.create_meal_plate(imagen, mime_type, food_history.id, food_text_dic)
            
            print("MealPlate creado exitosamente:", meal_plate)

            self.call_nutritional_api_resource(nutritional_api_dic, meal_plate ,current_user)
            
            # Asegurar que todo se guarda correctamente
            self.session.commit()
            return meal_plate.id

        except HTTPException as http_exc:
            print(f"Error HTTP: {http_exc.detail}")
            self.session.rollback()  
            raise http_exc
        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            self.session.rollback()
            raise HTTPException(status_code=500, detail="Error interno del servidor")

    def clean_data(self, data: str) -> dict:
        print("\n\n\nLos datos recibidos de Gemini son: ", data)
        match = re.search(r"food\s*=\s*({.*?})", data, re.DOTALL)
        if match:
            dict_str = match.group(1)
            food_dict = {}
            items = dict_str[1:-1].split(",")  # Eliminar llaves y separar
            for item in items:
                # Verificar que el item contiene ":"
                if ":" not in item:
                    print(f"Elemento mal formateado: {item} - saltando")
                    continue

                key_value = item.split(":", 1)  # Limitar a un solo split
                key = key_value[0].strip().strip("'\"")
                value = key_value[1].strip()
                try:
                    value = int(value)
                except ValueError:
                    pass
                food_dict[key] = value
            print("Diccionario de alimentos extraído")
            # A todas los values del diccionario se los convierte en float
            for key in food_dict:
                if isinstance(food_dict[key], str):
                    try:
                        food_dict[key] = float(food_dict[key])
                    except ValueError:
                        pass 
            return food_dict
        else:
            print("No se encontró el diccionario en el texto.")
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
                print("La imagen no ha cambiado de peso y sus dimensiones son las mismas.")
            else:
                print(f"Peso final: {final_size_kb:.2f} KB con calidad {quality}")
                print(f"Dimensiones finales: {image.size}")
            print("Imagen comprimida")
            return compressed_data
        else:
            print("La imagen es demasiado pequeña para ser comprimida.")
            return image_data
    

    def call_nutritional_api_resource(self, food_dic, meal_plate: MealPlate ,current_user: User) -> None:
        try:
            nutritionix_resource = NutritionixResource(self.session, current_user)
            nutritionix_resource.orquest(food_dic, meal_plate)
    
            self.session.commit()
        
            print("Se ha llamado a la Api Nutricional")
        except Exception as e:
            self.session.rollback()
            print(f"Error al procesar la información nutricional: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error al procesar la información nutricional: {str(e)}")
