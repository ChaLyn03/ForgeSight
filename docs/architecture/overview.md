# Architecture Overview

ForgeSight is a containerized visual inspection platform. The default local deployment runs the UI, API, worker, data stores, and MLflow registry with Docker Compose.

## Components

```
Browser
  |
  | HTTP:3000
  v
React UI served by Nginx
  |
  | /api and /media proxy
  v
FastAPI service
  |       |        |
  |       |        +--> shared media volume
  |       |        +--> shared MLflow artifacts
  |       +----------> PostgreSQL
  +------------------> Redis queue
                       |
                       v
                 Dramatiq worker
                       |
                       +--> MLflow model registry
                       +--> shared media volume
                       +--> shared MLflow artifacts
                       +--> PostgreSQL results
```

## Runtime Services

- `web`: Vite-built React app served by Nginx. Publishes `localhost:3000` and proxies `/api` and `/media` to the API.
- `api`: FastAPI app. Publishes `localhost:8000`, runs Alembic migrations at startup, and exposes `/health/live`, `/health/ready`, and Swagger at `/docs`.
- `worker`: Dramatiq worker. Consumes Redis jobs and writes inference results back to the database.
- `postgres`: PostgreSQL database for users, inspections, media metadata, jobs, and results. It is internal to the Compose network.
- `redis`: Dramatiq broker. It is internal to the Compose network.
- `mlflow`: MLflow tracking and registry service. Publishes `localhost:5000`. Its artifact root is shared through `./ml/artifacts` so API training jobs and workers can read the same model files.

## Request Flow

1. A user registers or signs in and receives a JWT.
2. The UI creates an inspection through `POST /api/v1/inspections`.
3. The UI uploads image media through `POST /api/v1/inspections/{id}/media`.
4. The UI creates an inference job through `POST /api/v1/inference/jobs`.
5. The API stores the queued job in PostgreSQL and sends a Dramatiq message to Redis.
6. The worker marks the job running, reads the image from the shared media volume, loads the configured MLflow model, and runs inference.
7. The worker writes prediction metadata plus overlay and segmentation media paths.
8. The UI polls job status and fetches the completed result from `GET /api/v1/inference/results/{job_id}`.

## Model Behavior

The worker resolves the model from:

- `MLFLOW_MODEL_URI`, when provided
- `MLFLOW_MODEL_NAME` plus `MLFLOW_MODEL_STAGE`, defaulting to `forgesight-inspection-model` and `Production`
- fallback synthetic inference when MLflow or the model is unavailable

The fallback keeps the inspection workflow usable before a baseline model is trained. For model registry validation, train the baseline with:

```bash
docker compose exec api python /app/ml/train_baseline.py \
  --tracking-uri http://mlflow:5000 \
  --experiment forgesight-baseline \
  --model-name forgesight-inspection-model \
  --model-stage Production
```

## Deployment Notes

- Set a long random `SECRET_KEY` before any non-local deployment.
- Keep PostgreSQL, Redis, media storage, and MLflow artifacts persistent across restarts.
- For production, use managed PostgreSQL and Redis where possible, external object storage for media, and a durable MLflow backend/artifact store.
- Scale the API and worker independently. The worker count controls inference throughput.
- Keep `/health/ready` wired into service readiness checks because it verifies database connectivity.
- Run `make smoke` after deploys to verify auth, inspection creation, upload, inference, worker processing, and result media.

See [the developer architecture guide](../developer/ARCHITECTURE.md) for the longer component breakdown.
