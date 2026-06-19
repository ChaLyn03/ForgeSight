import dramatiq
from dramatiq.brokers.redis import RedisBroker
from forgesight_api.db.session import SessionLocal
from forgesight_api.db import models
from forgesight_api.storage import open_media_file, save_file_contents
from forgesight_api.ml.model import ModelLoader
from datetime import datetime
import time
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
broker = RedisBroker(url=redis_url)
dramatiq.set_broker(broker)


def process_inference(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(models.InferenceJob).filter_by(id=job_id).first()
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        db.add(job)
        db.commit()

        model = ModelLoader.get_model(
            model_name=None,
            model_stage=None,
            model_uri=None if job.model_version_id is None else job.model_version_id,
        )
        inspection = db.query(models.Inspection).filter_by(id=job.inspection_id).first()
        if inspection is None:
            job.status = "failed"
            job.error_code = "INSPECTION_NOT_FOUND"
            job.error_message = "Inspection not found"
            job.completed_at = datetime.utcnow()
            db.add(job)
            db.commit()
            return

        for media in inspection.media:
            try:
                contents = open_media_file(media.storage_key)
            except FileNotFoundError:
                continue

            start = time.time()
            result = model.infer(contents)
            latency_ms = int((time.time() - start) * 1000)

            overlay_key = None
            seg_key = None

            try:
                if result.get("overlay"):
                    meta = save_file_contents(result["overlay"])
                    overlay_key = meta.get("storage_key")
                if result.get("segmentation"):
                    meta2 = save_file_contents(result["segmentation"])
                    seg_key = meta2.get("storage_key")
            except Exception:
                # Derived artifacts are non-critical; keep the inference metadata.
                pass

            inf_res = models.InferenceResult(
                job_id=job.id,
                media_file_id=media.id,
                predicted_label=result.get("predicted_label"),
                confidence=int(result.get("confidence", 0)),
                segmentation_storage_key=seg_key,
                overlay_storage_key=overlay_key,
                latency_ms=latency_ms,
            )
            db.add(inf_res)
            db.commit()

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db.add(job)
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.query(models.InferenceJob).filter_by(id=job_id).first()
        if job is not None:
            job.status = "failed"
            job.error_code = "INFERENCE_ERROR"
            job.error_message = str(exc)[:1000]
            job.completed_at = datetime.utcnow()
            db.add(job)
            db.commit()
        raise
    finally:
        db.close()


@dramatiq.actor(max_retries=3)
def process_inference_job(job_id: str):
    return process_inference(job_id)
