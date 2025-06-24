from pydantic import BaseModel
from typing import List, Any, Generic, TypeVar

T = TypeVar('T')

class FoodHistoryBase(BaseModel):
    pass 

class FoodHistoryCreate(FoodHistoryBase):
    user_id: int  

class FoodHistoryUpdate(FoodHistoryBase):
    pass

class PaginationMetadata(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationMetadata