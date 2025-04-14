import os
import io
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Union
import re

load_dotenv()


class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está definido en el .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def analyze_image(self, image_data: bytes) -> Union[str, dict]:
        try:
            # Verificamos que la imagen sea válida
            image = Image.open(io.BytesIO(image_data))

            # Prompt detallado (podrías cargarlo desde un archivo si es muy largo)
            with open("in-context-learning/prompt.txt", "r") as f:
                prompt = f.read()

            # Enviar imagen y prompt
            response = self.model.generate_content([image, prompt])
            
            food_text_dic = self.clean_data(response.text)
            
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