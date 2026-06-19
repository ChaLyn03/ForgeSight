import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from .session import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255))
    display_name = Column(String(255))
    role = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    component_type = Column(String(255))
    part_identifier = Column(String(255))
    batch_identifier = Column(String(255))
    status = Column(String(50), default="open")
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    media = relationship("MediaFile", back_populates="inspection")


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    inspection_id = Column(String(36), ForeignKey("inspections.id"), nullable=False, index=True)
    storage_key = Column(String(1024), nullable=False)
    original_filename = Column(String(255))
    content_type = Column(String(100))
    file_size = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    sha256 = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="media")


class InferenceJob(Base):
    __tablename__ = "inference_jobs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    inspection_id = Column(String(36), ForeignKey("inspections.id"), nullable=False, index=True)
    model_version_id = Column(String(36), nullable=True)
    status = Column(String(50), default="queued")
    requested_by = Column(String(36), nullable=True)
    queued_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    results = relationship("InferenceResult", back_populates="job")


class InferenceResult(Base):
    __tablename__ = "inference_results"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    job_id = Column(String(36), ForeignKey("inference_jobs.id"), nullable=False, index=True)
    media_file_id = Column(String(36), ForeignKey("media_files.id"), nullable=False, index=True)
    predicted_label = Column(String(255), nullable=True)
    confidence = Column(Integer, nullable=True)
    anomaly_score = Column(Integer, nullable=True)
    defect_area_ratio = Column(Integer, nullable=True)
    segmentation_storage_key = Column(String(1024), nullable=True)
    overlay_storage_key = Column(String(1024), nullable=True)
    bounding_boxes = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("InferenceJob", back_populates="results")
