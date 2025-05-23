from sqlmodel import Session, select
from fastapi import HTTPException
from models.clinical_data import ClinicalData
from schemas.clinical_data_schema import ClinicalDataCreate, ClinicalDataUpdate
from models.user import User

class ClinicalDataResource:
    def __init__(self, session: Session, current_user: User = None):
        self.session = session
        self.current_user = current_user

    def create(self, data: ClinicalDataCreate) -> ClinicalData:
        clinical_data = ClinicalData(**data.model_dump())
        self.session.add(clinical_data)
        self.session.commit()
        self.session.refresh(clinical_data)
        return clinical_data

    def get_all(self):
        return self.session.exec(select(ClinicalData)).all()
    
    def get_by_user_id(self, user_id: int):
        clinical_data = self.session.exec(select(ClinicalData).where(ClinicalData.user_id == user_id)).first()
        if not clinical_data:
            raise HTTPException(status_code=404, detail="ClinicalData no encontrado")
        return clinical_data

    def update(self, clinical_data_id: int, data: ClinicalDataUpdate) -> ClinicalData:
        clinical_data = self.session.get(ClinicalData, clinical_data_id)
        if not clinical_data:
            raise HTTPException(status_code=404, detail="ClinicalData no encontrado")
        for key, value in data.model_dump().items():
            setattr(clinical_data, key, value)
        self.session.add(clinical_data)
        self.session.commit()
        self.session.refresh(clinical_data)
        return clinical_data

    def delete(self, clinical_data_id: int):
        clinical_data = self.session.get(ClinicalData, clinical_data_id)
        if not clinical_data:
            raise HTTPException(status_code=404, detail="ClinicalData no encontrado")
        self.session.delete(clinical_data)
        self.session.commit()