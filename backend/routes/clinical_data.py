from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from resources.clinical_data_resource import ClinicalDataResource
from schemas.clinical_data_schema import ClinicalDataCreate, ClinicalDataUpdate

router = APIRouter(prefix="/clinical_data", tags=["clinical_data"])

@router.post("/")
def create_clinical_data(data: ClinicalDataCreate, session: Session = Depends(get_session)):
    resource = ClinicalDataResource(session)
    return resource.create(data)

@router.get("/")
def read_clinical_data(session: Session = Depends(get_session)):
    resource = ClinicalDataResource(session)
    return resource.get_all()

@router.put("/{clinical_data_id}")
def update_clinical_data(clinical_data_id: int, data: ClinicalDataUpdate, session: Session = Depends(get_session)):
    resource = ClinicalDataResource(session)
    return resource.update(clinical_data_id, data)

@router.delete("/{clinical_data_id}")
def delete_clinical_data(clinical_data_id: int, session: Session = Depends(get_session)):
    resource = ClinicalDataResource(session)
    resource.delete(clinical_data_id)
    return {"msg": "ClinicalData eliminada exitosamente"}