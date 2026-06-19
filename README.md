# ForgeSight

AI-assisted visual inspection and defect triage platform.

ForgeSight runs a React web UI, FastAPI backend, Dramatiq worker, PostgreSQL, Redis, and MLflow. The local Compose stack is the fastest path to a deployment-like environment.

## Local Deployment

```bash
cp .env.example .env
# Set SECRET_KEY in .env before using outside local development
docker compose up --build
```

Published services:

- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs
- MLflow: http://localhost:5000

PostgreSQL and Redis are internal Compose services by default. Use `docker compose exec postgres ...` and `docker compose exec redis ...` when you need direct access.

## Runtime Flow

1. Register or sign in through the web UI.
2. Create an inspection and upload an image.
3. The API writes metadata to PostgreSQL and stores uploaded media in the shared media volume.
4. The API queues inference work through Redis.
5. The worker loads the configured MLflow model, or falls back to synthetic inference if no model is registered.
6. Results, overlays, and segmentation masks are stored and displayed in the UI.

Compose shares `./ml/artifacts` with MLflow, the API, and the worker so model versions registered by the training command are loadable during inference.

To register the baseline model:

```bash
docker compose exec api python /app/ml/train_baseline.py \
  --tracking-uri http://mlflow:5000 \
  --experiment forgesight-baseline \
  --model-name forgesight-inspection-model \
  --model-stage Production
```

## Verify

```bash
make lint
make test
make audit
docker compose config
docker compose ps
```

The deployment smoke path verified for this repo is: register, login, create inspection, upload image, enqueue inference, wait for worker completion, and fetch result assets.

## Documentation

- [Quick start runbook](docs/developer/QUICKSTART.md)
- [Developer guide](docs/developer/DEVELOPER.md)
- [Architecture overview](docs/architecture/overview.md)
- [Detailed architecture notes](docs/developer/ARCHITECTURE.md)
- [ML baseline notes](ml/README.md)
