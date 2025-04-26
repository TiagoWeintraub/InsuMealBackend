import os 
import io
from dotenv import load_dotenv
import requests
from sqlmodel import Session, select
from fastapi import HTTPException


load_dotenv()

class EdamamResource:
    def __init__(self,  session: Session):
        self.session = session
        self.app_id = os.getenv("EDAMAM_APP_ID")
        self.app_key = os.getenv("EDAMAM_APP_KEY")
        self.page_size = 10
        if not self.app_id or not self.app_key:
            raise ValueError("EDAMAM_APP_ID o EDAMAM_APP_KEY no están definidos en el .env")
        self.base_url = os.getenv("EDAMAM_URL")

    def search_food_id_by_name(self, food_name: str):
        url = f"{self.base_url}?app_id={self.app_id}&app_key={self.app_key}&ingr={food_name}&pageSize={self.page_size}"
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error en la búsqueda: {response.status_code} - {response.text}")

    def get_food_by_id(self, food_name: str, ):
        # Primero buscamos el id del alimento
        food_data = self.search_food_id_by_name(food_name)
        
        if not food_data or 'hits' not in food_data or len(food_data['hits']) == 0:
            raise HTTPException(status_code=404, detail="Alimento no encontrado")
        
        # Extraemos el primer resultado
        food_item = food_data['hits'][0]['food']
        
        # Ahora podemos retornar el alimento
        return {
            "food_id": food_item.get("foodId"),
            "label": food_item.get("label"),
            "nutrients": food_item.get("nutrients")
        }