from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from resources.clinical_data_resource import ClinicalDataResource
from schemas.clinical_data_schema import ClinicalDataCreate, ClinicalDataUpdate
from auth.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/clinical_data", tags=["clinical_data"])

@router.get("/")
async def read_clinical_data(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    resource = ClinicalDataResource(session)
    return resource.get_all()

@router.get("/{clinical_data_id}")
async def read_clinical_data_by_id(clinical_data_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    resource = ClinicalDataResource(session)
    return resource.get_by_user_id(clinical_data_id)


@router.put("/{clinical_data_id}")
async def update_clinical_data(clinical_data_id: int, data: ClinicalDataUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    resource = ClinicalDataResource(session)
    return resource.update(clinical_data_id, data)


