import os
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy.exc import NoResultFound

import hashlib

from forgesight_api.storage import save_upload_file
from forgesight_api.db.session import SessionLocal
from forgesight_api.db import models
from forgesight_api import schemas
from fastapi import Depends
from forgesight_api.auth import get_current_user

router = APIRouter()

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))


@router.post("/inspections/{inspection_id}/media", response_model=List[schemas.MediaOut])
async def upload_media(inspection_id: str, files: List[UploadFile] = File(...), current_user: models.User = Depends(get_current_user)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []
    session = SessionLocal()
    try:
        # quick existence check for inspection
        try:
            session.query(models.Inspection).filter(models.Inspection.id == inspection_id).one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Inspection not found")

        for upload in files:
            if upload.content_type not in ALLOWED_MIME:
                raise HTTPException(status_code=400, detail=f"Unsupported media type: {upload.content_type}")

            contents_peek = await upload.read()
            # check size
            if len(contents_peek) > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="File too large")

            # compute sha and check for duplicates for idempotency
            sha256 = hashlib.sha256(contents_peek).hexdigest()
            existing = (
                session.query(models.MediaFile)
                .filter(models.MediaFile.inspection_id == inspection_id)
                .filter(models.MediaFile.sha256 == sha256)
                .one_or_none()
            )
            if existing is not None:
                # reuse existing media record
                results.append(existing)
                continue

            try:
                meta = await save_upload_file(contents=contents_peek)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            m = models.MediaFile(
                inspection_id=inspection_id,
                storage_key=meta["storage_key"],
                original_filename=upload.filename,
                content_type=upload.content_type,
                file_size=meta["file_size"],
                width=meta["width"],
                height=meta["height"],
                sha256=meta["sha256"],
            )
            session.add(m)
            session.flush()
            results.append(m)

        session.commit()
        # refresh to populate created_at
        for r in results:
            session.refresh(r)

        return results
    finally:
        session.close()
