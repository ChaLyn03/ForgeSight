from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from forgesight_api.db.session import SessionLocal
from forgesight_api.db import models
from fastapi import Depends
from forgesight_api.auth import get_current_user


router = APIRouter()


class InspectionCreate(BaseModel):
    component_type: str
    part_identifier: str | None = None
    batch_identifier: str | None = None
    notes: str | None = None


class InspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    component_type: str | None = None
    part_identifier: str | None = None
    batch_identifier: str | None = None
    status: str | None = None
    notes: str | None = None
    created_at: datetime | None = None


@router.post("/inspections", response_model=InspectionOut)
async def create_inspection(payload: InspectionCreate, current_user: models.User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        insp = models.Inspection(
            component_type=payload.component_type,
            part_identifier=payload.part_identifier,
            batch_identifier=payload.batch_identifier,
            notes=payload.notes,
        )
        session.add(insp)
        session.commit()
        session.refresh(insp)
        return insp
    finally:
        session.close()


@router.get("/inspections", response_model=list[InspectionOut])
async def list_inspections(current_user: models.User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        items = session.query(models.Inspection).order_by(models.Inspection.created_at.desc()).all()
        return items
    finally:
        session.close()


@router.get("/inspections/{inspection_id}", response_model=InspectionOut)
async def get_inspection(inspection_id: str, current_user: models.User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        item = session.query(models.Inspection).filter(models.Inspection.id == inspection_id).one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail="Inspection not found")
        return item
    finally:
        session.close()
