from sqlmodel import Session, select
from fastapi import HTTPException, status
from sqlalchemy import func, or_
import math
from models.user import User
from models.role import Role
from models.usage import Usage
from auth.jwt_handler import create_access_token
from schemas.user_schema import UserCreate, UserUpdate, PasswordChange, LoginInput, AdminUserUpdate
from schemas.clinical_data_schema import ClinicalDataCreate
from resources.clinical_data_resource import ClinicalDataResource
from schemas.food_history_schema import FoodHistoryCreate
from resources.food_history_resource import FoodHistoryResource

class UserResource:

    @staticmethod
    def _get_default_role_id(session: Session) -> int:
        role = session.exec(select(Role).where(Role.name == "user")).first()
        if not role:
            role = Role(name="user")
            session.add(role)
            session.commit()
            session.refresh(role)
        return role.id
    
    @staticmethod
    def create_user(data: UserCreate, session: Session) -> User:
        # Limpiar espacios en blanco del email
        clean_email = data.email.strip()
        
        # Verifica si ya existe el email
        if UserResource.get_user_by_email(clean_email, session):
            raise HTTPException(status_code=400, detail="Email ya registrado")
        
        # Validaciones para datos clínicos
        if not 0 <= data.ratio <= 100:
            raise HTTPException(status_code=400, detail="El ratio debe estar entre 0 y 100")
        
        if not 0 <= data.sensitivity <= 100:
            raise HTTPException(status_code=400, detail="La sensibilidad debe estar entre 0 y 100")

        if not 80 <= data.glycemiaTarget <= 130:
            raise HTTPException(status_code=400, detail="El objetivo glucémico debe estar entre 80 y 130")
        
        # 1. Crear primero el usuario sin relaciones
        user = User(
            name=data.name,
            lastName=data.lastName,
            email=clean_email,  # Usar el email limpio
            role_id=UserResource._get_default_role_id(session),
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
                glycemiaTarget = data.glycemiaTarget,
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
        # Limpiar espacios en blanco del email y retorna el usuario si existe, sino retorna None
        clean_email = email.strip()
        return session.exec(select(User).where(User.email == clean_email)).first()

    @staticmethod
    def get_user_by_id(user_id: int, session: Session):
        # Retorna el usuario si existe, sino retorna None
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return user

    @staticmethod
    def _get_role_by_name(role_name: str, session: Session) -> Role:
        role = session.exec(select(Role).where(Role.name == role_name)).first()
        if not role:
            raise HTTPException(status_code=400, detail=f"Rol inválido: {role_name}")
        return role

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
    def admin_update_user(user_id: int, data: AdminUserUpdate, session: Session):
        user = UserResource.get_user_by_id(user_id, session)

        if data.name is not None:
            user.name = data.name
        if data.lastName is not None:
            user.lastName = data.lastName
        if data.email is not None:
            clean_email = data.email.strip()
            existing = UserResource.get_user_by_email(clean_email, session)
            if existing and existing.id != user.id:
                raise HTTPException(status_code=400, detail="Email ya registrado")
            user.email = clean_email
        if data.role is not None:
            role_name = data.role.strip().lower()
            if role_name not in ("admin", "user"):
                raise HTTPException(status_code=400, detail="El rol debe ser 'admin' o 'user'")
            role = UserResource._get_role_by_name(role_name, session)
            user.role_id = role.id

        session.add(user)
        session.commit()
        session.refresh(user)
        role = session.get(Role, user.role_id)
        return {
            "id": user.id,
            "name": user.name,
            "lastName": user.lastName,
            "email": user.email,
            "role": role.name if role else "user",
        }

    @staticmethod
    def get_user_usage_summary(user_id: int, session: Session):
        UserResource.get_user_by_id(user_id, session)

        total_requests = int(
            session.exec(
                select(func.count(Usage.id)).where(Usage.user_id == user_id)
            ).one()
            or 0
        )

        rows = session.exec(
            select(
                Usage.provider,
                Usage.model_name,
                func.count(Usage.id),
                func.coalesce(func.sum(Usage.prompt_tokens), 0),
                func.coalesce(func.sum(Usage.completion_tokens), 0),
                func.coalesce(func.sum(Usage.total_tokens), 0),
            )
            .where(Usage.user_id == user_id)
            .group_by(Usage.provider, Usage.model_name)
        ).all()

        breakdown = []
        total_prompt = 0
        total_completion = 0
        total_tokens = 0

        for provider, model_name, requests, prompt, completion, total in rows:
            item = {
                "provider": provider,
                "model_name": model_name,
                "requests": int(requests or 0),
                "prompt_tokens": int(prompt or 0),
                "completion_tokens": int(completion or 0),
                "total_tokens": int(total or 0),
            }
            breakdown.append(item)
            total_prompt += item["prompt_tokens"]
            total_completion += item["completion_tokens"]
            total_tokens += item["total_tokens"]

        return {
            "user_id": user_id,
            "total_requests": total_requests,
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "breakdown": breakdown,
        }

    @staticmethod
    def get_users_count(session: Session) -> int:
        return int(session.exec(select(func.count(User.id))).one() or 0)

    @staticmethod
    def get_users_paginated(
        session: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
    ):
        query = select(User)
        normalized_search = (search or "").strip()

        if normalized_search:
            pattern = f"%{normalized_search}%"
            query = query.where(
                or_(
                    User.name.ilike(pattern),
                    User.lastName.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        total_count = int(session.exec(select(func.count()).select_from(query.subquery())).one() or 0)
        offset = (page - 1) * page_size

        users = session.exec(
            query.order_by(User.id.asc()).offset(offset).limit(page_size)
        ).all()

        role_ids = {u.role_id for u in users}
        roles = []
        if role_ids:
            roles = session.exec(select(Role).where(Role.id.in_(role_ids))).all()
        role_map = {r.id: r.name for r in roles}

        items = [
            {
                "id": u.id,
                "name": u.name,
                "lastName": u.lastName,
                "email": u.email,
                "role": role_map.get(u.role_id, "user"),
            }
            for u in users
        ]

        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
        }

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
        # Limpiar espacios en blanco del email
        clean_email = data.email.strip()
        
        user = session.exec(select(User).where(User.email == clean_email)).first()
        if not user or not user.validate_pass(data.password):
            raise HTTPException(status_code=400, detail="Credenciales inválidas")
        
        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer", "user_id": user.id}