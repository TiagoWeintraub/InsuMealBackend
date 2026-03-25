from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv
from models.clinical_data import ClinicalData
from models.food_history import FoodHistory
from models.ingredient import Ingredient
from models.meal_plate_ingredient import MealPlateIngredient
from models.meal_plate import MealPlate
from models.user import User
from models.role import Role
from models.usage import Usage
from sqlalchemy import text, inspect as sa_inspect
from sqlmodel import select

# Importar configuración para suprimir salidas
from utils.suppress_output import clean_console_output

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin1234@example.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "pass1234")
# Configurar logging de SQLAlchemy basado en variable de entorno
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
engine = create_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)

DEFAULT_INGREDIENTS = {
    "empanada dough": 51.11,
    "minced meat": 0.0,
    "meat": 0.01,
    "breadcrumbs": 71.98,
    "cheese": 3.09,
    "tomato sauce": 5.31,
    "french fries": 41.44,
    "spaghetti": 30.24,
    "bolognese sauce": 3.71,
    "grated cheese": 3.09,
    "whipped cream": 12.49,
    "cinnamon": 80.59,
    "lasagna": 9.01,
    "ground beef": 0.0,
    "potatoes": 21.15,
    "pasta": 30.86,
    "ham": 1.06,
    "chicken breast": 0.0,
    "lettuce": 3.29,
    "sauce": 7.43,
    "white rice": 28.17,
    "rice": 28.17,
    "shrimp": 1.52,
    "mussels": 7.39,
    "squid": 3.08,
    "peas": 15.63,
    "ice cream": 23.6,
    "cone": 84.1,
    "chocolate": 59.4,
    "mashed potatoes": 16.94,
    "hamburger bun": 50.15,
    "hamburger meat": 0.0,
    "tomato": 3.89,
    "cheddar cheese": 3.09,
    "thousand island": 14.64,
    "corn": 20.98,
    "risotto": 16.05,
    "microgreens": 3.6,
    "flan": 22.78,
    "strawberry": 7.68,
    "caramel": 57.01,
    "chicken": 0.05,
    "milk": 4.8,
    "chocolate cookie": 46.47,
    "vanilla cookie": 72.6,
    "pie crust": 56.24,
    "mustard": 5.83,
    "red rice": 23.51,
    "onion": 10.15,
    "carrot": 8.22,
    "potato": 21.15,
    "pumpkin": 4.9,
    "pea": 15.63,
    "eggplant": 8.73,
    "ketchup": 27.4,
    "bread": 49.42,
    "avocado": 8.53,
    "egg": 0.72,
    "pizza dough": 45.38,
    "prosciutto": 0.3,
    "arugula": 3.65,
    "barbecue": 18.74,
    "chicken patty": 12.84,
    "beef": 0.0,
    "mozzarella cheese": 2.19,
    "parmesan cheese": 13.91,
    "potato chips": 53.83,
    "beef patty": 0.0,
    "pickle": 2.41,
    "chicken thigh": 0.09,
    "chicken wing": 9.84,
    "soy sauce": 4.93,
    "clams": 5.13,
    "ground meat": 0.0,
    "ribs": 0.0,
    "parsley": 6.33,
    "black pepper": 63.95,
    "salsa": 6.64,
    "thousand islands": 14.64,
    "olive oil": 0.0,
    "bacon": 1.7,
    "red onion": 10.15,
    "dried herbs": 66.35,
    "oregano": 68.92,
    "herbs": 32.45,
    "brownie": 50.2,
    "cream cheese": 5.52,
    "blueberry": 14.49,
    "chocolate cake": 52.84,
    "berries": 10.87,
    "popcorn": 55.16,
    "candy": 98.0,
    "seasoning": 11.26,
    "pizza": 33.33,
    "water": 0.0,
    "pita bread": 55.7,
    "falafel": 18.62,
    "tahini sauce": 21.5,
    "potato pancake": 27.81,
    "mayonnaise": 0.57,
    "pepperoni": 1.18,
    "cola": 9.56,
    "pillsbury carb monitor dinner rolls": 15.71,
}


def init_db():
    try:
        print("Intentando crear tablas...")
        SQLModel.metadata.create_all(engine)
        user_role_id = _seed_default_roles()
        _backfill_existing_users_with_default_role(user_role_id)
        _ensure_usage_tracking_columns()
        _seed_default_ingredients()
        _seed_default_admin_user()
        print("Base de Datos lista.")
        clean_console_output()  # Limpiar salida después de crear las tablas
    except Exception as e:
        print(f"Puede que las tablas ya existieran: {e}")
        clean_console_output()


def _seed_default_roles() -> int:
    with Session(engine) as session:
        existing_roles = {
            role.name for role in session.exec(select(Role)).all()
        }
        to_create = []
        for role_name in ("admin", "user"):
            if role_name not in existing_roles:
                to_create.append(Role(name=role_name))

        if to_create:
            for role in to_create:
                session.add(role)
            session.commit()

        user_role = session.exec(select(Role).where(Role.name == "user")).first()
        return user_role.id


def _backfill_existing_users_with_default_role(user_role_id: int):
    inspector = sa_inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("user")}

    with engine.connect() as conn:
        dialect = conn.dialect.name

        if "role_id" not in columns:
            if dialect == "postgresql":
                conn.execute(text('ALTER TABLE "user" ADD COLUMN role_id INTEGER'))
            else:
                conn.execute(text("ALTER TABLE user ADD COLUMN role_id INTEGER"))
            conn.commit()

        if dialect == "postgresql":
            conn.execute(
                text('UPDATE "user" SET role_id = :role_id WHERE role_id IS NULL'),
                {"role_id": user_role_id},
            )
            conn.execute(text('ALTER TABLE "user" ALTER COLUMN role_id SET NOT NULL'))
            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu
                              ON tc.constraint_name = kcu.constraint_name
                             AND tc.table_schema = kcu.table_schema
                            WHERE tc.constraint_type = 'FOREIGN KEY'
                              AND tc.table_name = 'user'
                              AND kcu.column_name = 'role_id'
                        ) THEN
                            ALTER TABLE "user"
                            ADD CONSTRAINT fk_user_role_id
                            FOREIGN KEY (role_id) REFERENCES role (id);
                        END IF;
                    END
                    $$;
                    """
                )
            )
        else:
            conn.execute(
                text("UPDATE user SET role_id = :role_id WHERE role_id IS NULL"),
                {"role_id": user_role_id},
            )

        conn.commit()


def _ensure_usage_tracking_columns():
    inspector = sa_inspect(engine)
    table_names = set(inspector.get_table_names())
    if "usage" not in table_names:
        return

    columns = {col["name"] for col in inspector.get_columns("usage")}
    with engine.connect() as conn:
        dialect = conn.dialect.name
        if "provider" not in columns:
            if dialect == "postgresql":
                conn.execute(text('ALTER TABLE "usage" ADD COLUMN provider VARCHAR'))
                conn.execute(text("UPDATE usage SET provider = 'google' WHERE provider IS NULL"))
                conn.execute(text('ALTER TABLE "usage" ALTER COLUMN provider SET NOT NULL'))
            else:
                conn.execute(text("ALTER TABLE usage ADD COLUMN provider VARCHAR"))
                conn.execute(text("UPDATE usage SET provider = 'google' WHERE provider IS NULL"))

        if "model_name" not in columns:
            if dialect == "postgresql":
                conn.execute(text('ALTER TABLE "usage" ADD COLUMN model_name VARCHAR'))
                conn.execute(
                    text(
                        "UPDATE usage SET model_name = 'gemini-2.5-flash-lite' WHERE model_name IS NULL"
                    )
                )
                conn.execute(text('ALTER TABLE "usage" ALTER COLUMN model_name SET NOT NULL'))
            else:
                conn.execute(text("ALTER TABLE usage ADD COLUMN model_name VARCHAR"))
                conn.execute(
                    text(
                        "UPDATE usage SET model_name = 'gemini-2.5-flash-lite' WHERE model_name IS NULL"
                    )
                )

        conn.commit()


def _seed_default_ingredients():
    with Session(engine) as session:
        existing_names = {
            str(name).strip().lower()
            for name in session.exec(select(Ingredient.name)).all()
            if name
        }
        to_create = []

        for name, carbs in DEFAULT_INGREDIENTS.items():
            normalized_name = name.strip().lower()
            if not normalized_name or normalized_name in existing_names:
                continue
            to_create.append(
                Ingredient(
                    name=normalized_name,
                    carbsPerHundredGrams=float(carbs),
                )
            )
            existing_names.add(normalized_name)

        if to_create:
            for ingredient in to_create:
                session.add(ingredient)
            session.commit()


def _seed_default_admin_user():
    with Session(engine) as session:
        existing_admin = session.exec(
            select(User).where(User.email == DEFAULT_ADMIN_EMAIL)
        ).first()
        if existing_admin:
            return

        admin_role = session.exec(select(Role).where(Role.name == "admin")).first()
        if not admin_role:
            admin_role = Role(name="admin")
            session.add(admin_role)
            session.commit()
            session.refresh(admin_role)

        admin_user = User(
            name="Admin",
            lastName="System",
            email=DEFAULT_ADMIN_EMAIL,
            role_id=admin_role.id,
        )
        admin_user.plain_password = DEFAULT_ADMIN_PASSWORD
        session.add(admin_user)
        session.commit()


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