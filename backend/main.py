from fastapi import FastAPI
from routes.routes import router as api_router
from dotenv import load_dotenv
from database import init_db

load_dotenv()  

app = FastAPI()

# Inicializar la base de datos
init_db()

# Incluir las rutas
app.include_router(api_router)