from fastapi import FastAPI
from routes.routes import router as api_router
from dotenv import load_dotenv

load_dotenv()  # Carga las variables de entorno

app = FastAPI()

# Incluir las rutas
app.include_router(api_router)
