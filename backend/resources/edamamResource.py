import os 
import io
from dotenv import load_dotenv
import requests

load_dotenv()

class EdamamResource:
    def __init__(self):
        self.app_id = os.getenv("EDAMAM_APP_ID")
        self.app_key = os.getenv("EDAMAM_APP_KEY")
        self.page_size = 10
        if not self.app_id or not self.app_key:
            raise ValueError("EDAMAM_APP_ID o EDAMAM_APP_KEY no están definidos en el .env")
        self.base_url = "https://api.edamam.com/api/food-database/v2/parser"

    def post_search_food_id_by_name(self, food_name: str):
        url = f"{self.base_url}?app_id={self.app_id}&app_key={self.app_key}&ingr={food_name}&pageSize={self.page_size}"
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error en la búsqueda: {response.status_code} - {response.text}")

    # def get_food_by_id(self, food_name: str):