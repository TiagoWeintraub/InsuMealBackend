from pydantic import BaseModel

class ClinicalDataBase(BaseModel):
    pass

class ClinicalDataCreate(ClinicalDataBase):
    ratio: float
    sensitivity: float
    glycemiaTarget: int
    user_id: int


class ClinicalDataUpdate(ClinicalDataBase):
    ratio: float
    sensitivity: float
    glycemiaTarget: int
