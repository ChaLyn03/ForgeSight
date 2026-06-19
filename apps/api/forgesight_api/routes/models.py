from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from typing import Optional

router = APIRouter(prefix="/models", tags=["models"])


class ModelVersion(BaseModel):
    name: str
    version: str
    stage: str
    status: str
    creation_timestamp: Optional[int] = None


class ModelInfo(BaseModel):
    name: str
    latest_version: str
    stages: dict[str, str]  # stage -> version
    versions: list[ModelVersion]


@router.get("/registry", response_model=list[ModelInfo])
async def list_models():
    """
    List all registered models from MLflow registry.
    Returns model names, versions, and stage info.
    """
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise HTTPException(status_code=503, detail="MLflow tracking URI not configured")

    try:
        import mlflow
        mlflow.set_tracking_uri(tracking_uri)
        client = mlflow.tracking.MlflowClient()

        models = []
        registered_models = client.search_registered_models()

        for rm in registered_models:
            versions = []
            stages_dict = {}

            for mv in rm.latest_versions:
                version_info = ModelVersion(
                    name=rm.name,
                    version=mv.version,
                    stage=mv.current_stage,
                    status=mv.status,
                    creation_timestamp=mv.creation_timestamp,
                )
                versions.append(version_info)
                if mv.current_stage:
                    stages_dict[mv.current_stage] = mv.version

            if versions:
                model_info = ModelInfo(
                    name=rm.name,
                    latest_version=versions[0].version,
                    stages=stages_dict,
                    versions=versions,
                )
                models.append(model_info)

        return models

    except ImportError:
        raise HTTPException(status_code=503, detail="MLflow not installed")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MLflow error: {str(exc)}")


class TransitionRequest(BaseModel):
    model_name: str
    version: str
    stage: str
    archive_existing: bool = True


@router.post("/transition-stage")
async def transition_model_stage(req: TransitionRequest):
    """
    Transition a model version to a new stage (e.g., Production, Staging, Archived).
    """
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise HTTPException(status_code=503, detail="MLflow tracking URI not configured")

    try:
        import mlflow

        mlflow.set_tracking_uri(tracking_uri)
        client = mlflow.tracking.MlflowClient()

        client.transition_model_version_stage(
            name=req.model_name,
            version=req.version,
            stage=req.stage,
            archive_existing_versions=req.archive_existing,
        )

        return {
            "status": "success",
            "message": f"Model {req.model_name} v{req.version} transitioned to {req.stage}",
        }

    except ImportError:
        raise HTTPException(status_code=503, detail="MLflow not installed")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MLflow error: {str(exc)}")
