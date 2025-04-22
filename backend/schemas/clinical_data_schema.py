from pydantic import BaseModel

class ClinicalDataBase(BaseModel):
    pass

class ClinicalDataCreate(ClinicalDataBase):
    ratio: float
    sensitivity: float
    user_id: int


class ClinicalDataUpdate(ClinicalDataBase):
    pass