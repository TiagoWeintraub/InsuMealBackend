from sqlmodel import Session, select
from fastapi import HTTPException, status
from models.user import User
from auth.jwt_handler import create_access_token
from schemas.user_schema import UserCreate, UserUpdate, PasswordChange, LoginInput
from schemas.clinical_data_schema import ClinicalDataCreate
from resources.clinical_data_resource import ClinicalDataResource
from schemas.food_history_schema import FoodHistoryCreate
from resources.food_history_resource import FoodHistoryResource

class UserResource:
    
    @staticmethod
    def create_user(data: UserCreate, session: Session) -> User:
        # Verifica si ya existe el email
        if UserResource.get_user_by_email(data.email, session):
            raise HTTPException(status_code=400, detail="Email ya registrado")
        
            # Verifica si ya existe el email

        # Validaciones para datos clínicos
        if not 0 <= data.ratio <= 100:
            raise HTTPException(status_code=400, detail="El ratio debe estar entre 0 y 100")
        
        if not 0 <= data.sensitivity <= 100:
            raise HTTPException(status_code=400, detail="La sensibilidad debe estar entre 0 y 100")

        if not 80 <= data.glycemicTarget <= 130:
            raise HTTPException(status_code=400, detail="El objetivo glucémico debe estar entre 80 y 130")
        
        # 1. Crear primero el usuario sin relaciones
        user = User(
            name=data.name,
            lastName=data.lastName,
            email=data.email
        )
        user.plain_password = data.password

        session.add(user)
        session.commit()
        session.refresh(user)  # Ahora user.id está asignado
        
        # 2. Crear ClinicalData asociándoselo al usuario
        clinical_data_resource = ClinicalDataResource(session)
        clinical_data = clinical_data_resource.create(
            ClinicalDataCreate(
                ratio= data.ratio,
                sensitivity= data.sensitivity,
                glycemicTarget = data.glycemicTarget,
                user_id=user.id
                )
        )
        
        session.add(clinical_data)
        session.commit()
        session.refresh(clinical_data)
        
        # 3. Crear FoodHistory asociándoselo al usuario
        food_history_resource = FoodHistoryResource(session)
        food_history = food_history_resource.create(
            FoodHistoryCreate(user_id=user.id)
        )
        session.add(food_history)
        session.commit()
        session.refresh(food_history)

        return user

    @staticmethod
    def get_all_users(session: Session): 
        return session.exec(select(User)).all()
    
    @staticmethod
    def get_user_by_email(email: str, session: Session):
        # Retorna el usuario si existe, sino retorna None
        return session.exec(select(User).where(User.email == email)).first()

    @staticmethod
    def get_user_by_id(user_id: int, session: Session):
        # Retorna el usuario si existe, sino retorna None
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return user

    # ... (el resto de métodos permanece igual)
    @staticmethod
    def update_user(data: UserUpdate, current_user: User, session: Session):
        current_user.name = data.name
        current_user.lastName = data.lastName
        session.add(current_user)
        session.commit()
        session.refresh(current_user)
        return current_user

    @staticmethod
    def delete_by_id(user_id: int, session: Session):
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        session.delete(user)
        session.commit()
        return {"msg": "Usuario eliminado exitosamente"}

    @staticmethod
    def change_password(data: PasswordChange, current_user: User, session: Session):
        if not current_user.validate_pass(data.old_password):
            raise HTTPException(status_code=403, detail="Contraseña actual incorrecta")
        current_user.plain_password = data.new_password
        session.add(current_user)
        session.commit()
        return {"msg": "Contraseña actualizada exitosamente"}

    @staticmethod
    def login_user(data: LoginInput, session: Session):
        user = session.exec(select(User).where(User.email == data.email)).first()
        if not user or not user.validate_pass(data.password):
            raise HTTPException(status_code=400, detail="Credenciales inválidas")
        
        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer", "user_id": user.id}