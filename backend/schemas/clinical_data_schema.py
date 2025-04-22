from pydantic import BaseModel

class ClinicalDataBase(BaseModel):
    info: str

class ClinicalDataCreate(ClinicalDataBase):
    ratio: float
    sensitivity: float
    user_id: int


class ClinicalDataUpdate(ClinicalDataBase):
    pass