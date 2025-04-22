from pydantic import BaseModel

class FoodHistoryBase(BaseModel):
    description: str

class FoodHistoryCreate(FoodHistoryBase):
    user_id: int  

class FoodHistoryUpdate(FoodHistoryBase):
    pass