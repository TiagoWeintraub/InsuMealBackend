from fastapi import FastAPI
from routes.gemini import router as api_router
from dotenv import load_dotenv
from database import init_db


load_dotenv()  

app = FastAPI()

# Inicializar la base de datos
init_db()

# Como tengo muchos archivos de rutas, los voy a incluir a todos

# Incluir las rutas de Gemini 

# Incluir las rutas
app.include_router(api_router)