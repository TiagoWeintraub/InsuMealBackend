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

# Importar configuración para suprimir salidas
from utils.suppress_output import clean_console_output

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# Configurar logging de SQLAlchemy basado en variable de entorno
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
engine = create_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)

def init_db():
    try:
        print("Intentando crear tablas...")
        SQLModel.metadata.create_all(engine)
        print("Base de Datos lista.")
        clean_console_output()  # Limpiar salida después de crear las tablas
    except Exception as e:
        print(f"Puede que las tablas ya existieran: {e}")
        clean_console_output()


def drop_db():
    try:
        print("Intentando eliminar esquema público con CASCADE...")
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.commit()
        print("Esquema eliminado y recreado.")
        clean_console_output()  # Limpiar salida después de operaciones de BD
    except Exception as e:
        print(f"Error al eliminar esquema: {e}")
        clean_console_output()

def get_session():
    with Session(engine) as session:
        yield session

def inspector():
    try:
        tablas = list(SQLModel.metadata.tables.keys())
        print("Tablas en la base de datos:")

        for tabla in tablas:
            print(f"- {tabla}") 
        
        clean_console_output()  # Limpiar salida después de inspeccionar
        return tablas
            
    except Exception as e:
        print(f"Error al inspeccionar tablas: {e}")
        clean_console_output()
        return []