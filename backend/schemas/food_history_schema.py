from pydantic import BaseModel

class FoodHistoryBase(BaseModel):
    pass 

class FoodHistoryCreate(FoodHistoryBase):
    user_id: int  

class FoodHistoryUpdate(FoodHistoryBase):
    pass