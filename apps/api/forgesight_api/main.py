import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from forgesight_api.db.session import engine
from forgesight_api.routes.media import router as media_router
from forgesight_api.routes.inspections import router as inspections_router
from forgesight_api.routes.auth import router as auth_router
from forgesight_api.routes.inference import router as inference_router
from forgesight_api.routes.models import router as models_router
from forgesight_api.storage import get_media_root


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_media_root().mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="ForgeSight API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/media",
    StaticFiles(directory=str(get_media_root()), check_dir=False),
    name="media",
)


@app.get("/health/live")
async def live():
    return {"status": "ok"}


@app.get("/health/ready")
async def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {"status": "ready"}


# API routers
app.include_router(media_router, prefix="/api/v1")
app.include_router(inspections_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(inference_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
