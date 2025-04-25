from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv
from models.clinical_data import ClinicalData
from models.food_history import FoodHistory
from models.ingredient import Ingredient
from models.meal_plate_ingredient import MealPlateIngredient
from models.meal_plate import MealPlate
from models.user import User
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    try:
        print("Intentando crear tablas...")
        SQLModel.metadata.create_all(engine)
        print("\nTablas creadas.")
    except Exception as e:
        print(f"\nPuede que las tablas ya existieran: {e}")


def drop_db():
    try:
        print("Intentando eliminar esquema público con CASCADE...")
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.commit()
        print("\nEsquema eliminado y recreado.")
    except Exception as e:
        print(f"\nError al eliminar esquema: {e}")

def get_session():
    with Session(engine) as session:
        yield session

def inspector():
    try:
        tablas = list(SQLModel.metadata.tables.keys())
        print("\n\nTablas en la base de datos:")

        for tabla in tablas:
            print(f"\n- {tabla}\n") 
        return tablas
            
    except Exception as e:
        print(f"Error al inspeccionar tablas: {e}")
        return []