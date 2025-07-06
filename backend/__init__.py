from fastapi import FastAPI
from routes.gemini import router as gemini_router
from dotenv import load_dotenv
from database import init_db, inspector
from database import drop_db
from routes.user import router as user_router
from routes.clinical_data import router as clinical_data_router
from routes.food_history import router as food_history_router
from routes.ingredient import router as ingredient_router
from routes.meal_plate import router as meal_plate_router
from routes.auth import router as auth_router
from routes.meal_plate_ingredient import router as meal_plate_ingredient_router
from routes.nutritionix import router as nutritional_router
from routes.dosis import router as dosis_router

# Configurar supresión de salidas problemáticas al inicio de la aplicación
from utils.suppress_output import clean_console_output

load_dotenv()  

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API InsuMeal funcionando"}


# drop_db()  # Descomentar para borrar la base de datos antes de crearla

inspector() 

init_db()

# Incluir las rutas
app.include_router(gemini_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(clinical_data_router)
app.include_router(food_history_router)
app.include_router(ingredient_router)
app.include_router(meal_plate_router)
app.include_router(meal_plate_ingredient_router)
app.include_router(nutritional_router)
app.include_router(dosis_router)

# Limpiar salida de consola al final de la inicialización
clean_console_output()