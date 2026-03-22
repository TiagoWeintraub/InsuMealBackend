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

def init_db():
    try:
        print("Intentando crear tablas...")
        SQLModel.metadata.create_all(engine)
        user_role_id = _seed_default_roles()
        _backfill_existing_users_with_default_role(user_role_id)
        _ensure_usage_tracking_columns()
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