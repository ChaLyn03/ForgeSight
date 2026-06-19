from datetime import datetime
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from forgesight_api.auth import get_current_user
from forgesight_api.db import models
from forgesight_api.db.session import SessionLocal
from forgesight_api.storage import media_url_for_storage_key
from forgesight_api.worker.worker import process_inference_job, process_inference

router = APIRouter(prefix="/inference", tags=["inference"])


class InferenceRequest(BaseModel):
    inspection_id: str
    model_version_id: str | None = None


class InferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    status: str
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


class InferenceResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    media_file_id: str
    predicted_label: str | None = None
    confidence: int | None = None
    anomaly_score: int | None = None
    defect_area_ratio: int | None = None
    segmentation_storage_key: str | None = None
    overlay_storage_key: str | None = None
    segmentation_url: str | None = None
    overlay_url: str | None = None
    bounding_boxes: str | None = None
    latency_ms: int | None = None
    created_at: datetime | None = None


def _result_to_out(result: models.InferenceResult) -> InferenceResultOut:
    return InferenceResultOut(
        id=result.id,
        job_id=result.job_id,
        media_file_id=result.media_file_id,
        predicted_label=result.predicted_label,
        confidence=result.confidence,
        anomaly_score=result.anomaly_score,
        defect_area_ratio=result.defect_area_ratio,
        segmentation_storage_key=result.segmentation_storage_key,
        overlay_storage_key=result.overlay_storage_key,
        segmentation_url=media_url_for_storage_key(result.segmentation_storage_key),
        overlay_url=media_url_for_storage_key(result.overlay_storage_key),
        bounding_boxes=result.bounding_boxes,
        latency_ms=result.latency_ms,
        created_at=result.created_at,
    )


def _process_sync_and_refresh(db, job: models.InferenceJob) -> None:
    process_inference(job.id)
    db.expire(job)
    db.refresh(job)


@router.post("/jobs", response_model=InferenceOut)
async def create_job(req: InferenceRequest, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        inspection = db.query(models.Inspection).filter_by(id=req.inspection_id).one_or_none()
        if inspection is None:
            raise HTTPException(status_code=404, detail="Inspection not found")

        job = models.InferenceJob(
            inspection_id=req.inspection_id,
            model_version_id=req.model_version_id,
            requested_by=user.id,
            status="queued",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        if os.getenv("FORCE_SYNC_INFERENCE", "0") == "1":
            _process_sync_and_refresh(db, job)
            return job

        try:
            process_inference_job.send(job.id)
        except Exception:
            if os.getenv("INFERENCE_SYNC_FALLBACK", "1") != "1":
                raise
            _process_sync_and_refresh(db, job)

        return job
    finally:
        db.close()


@router.get("/jobs/{job_id}", response_model=InferenceOut)
async def get_job(job_id: str, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        job = db.query(models.InferenceJob).filter_by(id=job_id).one_or_none()
        if job is None:
            raise HTTPException(status_code=404, detail="Inference job not found")
        return job
    finally:
        db.close()


@router.get("/inspections/{inspection_id}/jobs/latest", response_model=InferenceOut)
async def get_latest_job_for_inspection(inspection_id: str, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        job = (
            db.query(models.InferenceJob)
            .filter_by(inspection_id=inspection_id)
            .order_by(models.InferenceJob.queued_at.desc())
            .first()
        )
        if job is None:
            raise HTTPException(status_code=404, detail="Inference job not found")
        return job
    finally:
        db.close()


@router.get("/results/{job_id}", response_model=InferenceResultOut)
async def get_result(job_id: str, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = (
            db.query(models.InferenceResult)
            .filter_by(job_id=job_id)
            .order_by(models.InferenceResult.created_at.asc())
            .first()
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Inference result not found")
        return _result_to_out(result)
    finally:
        db.close()
