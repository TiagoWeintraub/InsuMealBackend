from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine.url import make_url

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)

def create_db_if_not_exists():
    url = make_url(DATABASE_URL)
    # Forzamos el nombre a minúsculas para que coincida con lo que almacena Postgres
    database_name = url.database.lower()

    # Conéctate a la base de datos por defecto: postgres
    default_url = url.set(database="postgres")
    default_engine = create_engine(default_url)

    with default_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        result = connection.execute(
            text("SELECT 1 FROM pg_database WHERE lower(datname) = :dbname"),
            {"dbname": database_name}
        )
        exists = result.scalar() is not None
        if not exists:
            connection.execute(text(f"CREATE DATABASE {database_name}"))
            print(f"Database {database_name} created.")
        else:
            print(f"Database {database_name} already exists.")

def init_db():
    create_db_if_not_exists()
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session