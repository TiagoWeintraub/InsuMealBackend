from sqlmodel import Session, select, func
from fastapi import HTTPException
from models.food_history import FoodHistory
from models.meal_plate import MealPlate
from schemas.food_history_schema import FoodHistoryCreate, FoodHistoryUpdate, PaginatedResponse, PaginationMetadata
import math

class FoodHistoryResource:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: FoodHistoryCreate) -> FoodHistory:
        food_history = FoodHistory(**data.model_dump())
        self.session.add(food_history)
        self.session.commit()
        self.session.refresh(food_history)
        return food_history

    def get_by_user_id(self, user_id: int):
        food_history = self.session.exec(select(FoodHistory).where(FoodHistory.user_id == user_id)).first()
        if not food_history:
            raise HTTPException(status_code=404, detail="FoodHistory no encontrado")
        return food_history

    def get_all(self):
        return self.session.exec(select(FoodHistory)).all()

    def get_user_meal_plates_paginated(self, user_id: int, page: int = 1, page_size: int = 10) -> PaginatedResponse:
        """
        Obtiene los platos de comida del historial de un usuario con paginación
        """
        # Verificar que el usuario tiene historial de comidas
        food_history = self.session.exec(
            select(FoodHistory).where(FoodHistory.user_id == user_id)
        ).first()
        
        if not food_history:
            raise HTTPException(status_code=404, detail="Historial de comidas no encontrado para este usuario")
        
        # Contar el total de meal_plates para este food_history
        total_count = self.session.exec(
            select(func.count(MealPlate.id)).where(MealPlate.food_history_id == food_history.id)
        ).one()
        
        # Calcular offset
        offset = (page - 1) * page_size
        
        # Obtener los meal_plates paginados, ordenados por fecha de creación (más recientes primero)
        meal_plates = self.session.exec(
            select(MealPlate)
            .where(MealPlate.food_history_id == food_history.id)
            .order_by(MealPlate.id.desc())  # Ordenar por ID descendente (más recientes primero)
            .offset(offset)
            .limit(page_size)
        ).all()
        
        # Calcular metadatos de paginación
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        has_next = page < total_pages
        has_previous = page > 1
        
        pagination_metadata = PaginationMetadata(
            page=page,
            page_size=page_size,
            total_items=total_count,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
        
        return PaginatedResponse(
            items=meal_plates,
            pagination=pagination_metadata
        )

    def update(self, food_history_id: int, data: FoodHistoryUpdate) -> FoodHistory:
        food_history = self.session.get(FoodHistory, food_history_id)
        if not food_history:
            raise HTTPException(status_code=404, detail="FoodHistory no encontrado")
        for key, value in data.model_dump().items():
            setattr(food_history, key, value)
        self.session.add(food_history)
        self.session.commit()
        self.session.refresh(food_history)
        return food_history

    def delete(self, food_history_id: int):
        food_history = self.session.get(FoodHistory, food_history_id)
        if not food_history:
            raise HTTPException(status_code=404, detail="FoodHistory no encontrado")
        self.session.delete(food_history)
        self.session.commit()