import os
import io
from PIL import Image, ImageOps
from PIL.Image import Resampling
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Union
import re

load_dotenv()

class GeminiResource:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está definido en el .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")

    def analyze_image(self, image_data: bytes) -> Union[str, dict]:
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
            
            # Este food dict se debe enviar al recurso de Edamam,
            # Se debe crear un meal plate y asociarlo al historial de comidas del usuario
            # cada alimento de edamam se debe guardar en la base de datos como ingrediente

            
            return food_text_dic

        except Exception as e:
            return {"error": str(e)}

    def clean_data(self, data: str) -> dict:
        match = re.search(r"food\s*=\s*({.*?})", data, re.DOTALL)

        if match:
            dict_str = match.group(1)

            # Crear un diccionario vacío
            food_dict = {}

            # Dividir la cadena en pares clave-valor
            items = dict_str[1:-1].split(",")  # Eliminar las llaves y dividir por comas

            for item in items:
                # Dividir cada par clave-valor por dos puntos
                key_value = item.split(":")

                # Limpiar la clave y el valor
                key = key_value[0].strip().strip("'\"")  # Eliminar espacios y comillas
                value = key_value[1].strip()

                # Convertir el valor a entero si es posible
                try:
                    value = int(value)
                except ValueError:
                    pass  # Si no es un entero, dejarlo como cadena
                
                # Agregar la clave y el valor al diccionario
                food_dict[key] = value

            return food_dict
        else:
            print("No se encontró el diccionario en el texto.")

    def reduce_image_weight(self, image_data: bytes, target_max_kb=500) -> bytes:
        target_max_bytes = target_max_kb * 1024
        image = Image.open(io.BytesIO(image_data))
        image = ImageOps.exif_transpose(image)  # Corrige orientación
        
        print(f"Peso original en MB: {len(image_data) / (1024 * 1024):.2f} MB")
        print(f"Dimensiones originales: {image.size}")

        # Convertimos a RGB si hace falta
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Redimensionamos si es muy grande
        max_dimension = 1024  # Puedes ajustar esto según tu app
        if max(image.size) > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Resampling.LANCZOS)

        # Comprimimos iterativamente hasta que pese menos que el target
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

        # with open("imagen_comprimida.jpg", "wb") as f: # Guardamos la imagen comprimida
        #     f.write(compressed_data) 

        return compressed_data


