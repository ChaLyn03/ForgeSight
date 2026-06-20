# Production Deployment Plan

ForgeSight is deployment-ready for a single-host Docker Compose environment and has a clear path to managed infrastructure.

## Required Decisions

- Runtime target: VPS, ECS, Kubernetes, Fly.io, Render, Railway, or another container platform.
- Database: managed PostgreSQL strongly preferred outside local development.
- Queue: managed Redis strongly preferred outside local development.
- Artifacts and media: persistent object storage or mounted durable volumes.
- TLS and domain: terminate HTTPS before the web/API entrypoint.
- Secrets: use the platform secret store, not committed `.env` files.

## Compose Baseline

The root `docker-compose.yml` is suitable for local and single-host validation:

```bash
cp .env.production.example .env
docker compose up --build -d
make smoke
```

Published services:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- MLflow: `http://localhost:5000`

Internal-only services:

- PostgreSQL
- Redis

## Persistent Data

Keep these durable across deploys:

- PostgreSQL data volume or managed database
- Redis data only if broker durability is required by the chosen deployment mode
- `/app/storage` media volume used by API and worker
- `/mlflow/artifacts` model artifact path shared by MLflow, API, and worker
- MLflow backend store

For cloud production, prefer object storage for media and model artifacts. If using Compose, back up Docker volumes and `./ml/artifacts`.

## Environment

Start from `.env.production.example` and set:

- `SECRET_KEY`: at least 32 random bytes
- `POSTGRES_PASSWORD` or external `DATABASE_URL`
- `REDIS_URL`
- `CORS_ORIGINS`: exact HTTPS web origins
- `MLFLOW_TRACKING_URI`
- `MLFLOW_MODEL_NAME`
- `MLFLOW_MODEL_STAGE`

Do not expose PostgreSQL or Redis to the public internet.

## Release Checklist

1. Run `make lint`.
2. Run `make test`.
3. Run `make audit`.
4. Build the stack with `docker compose build`.
5. Start the stack with `docker compose up -d`.
6. Verify health with `docker compose ps`.
7. Run `make smoke`.
8. Register or promote the intended MLflow Production model.
9. Confirm worker logs show `Loaded MLflow PyTorch model` when inference runs.
10. Snapshot or back up persistent storage.

## Operations

Useful commands:

```bash
docker compose ps
docker compose logs -f api worker
docker compose exec postgres psql -U forgesight -d forgesight
docker compose exec redis redis-cli ping
make smoke
```

Health endpoints:

- API readiness: `/health/ready`
- API liveness: `/health/live`
- MLflow health: `/health`

## Scale-Out Path

For higher availability:

- Run multiple API replicas behind a load balancer.
- Run worker replicas independently based on inference queue depth.
- Move PostgreSQL and Redis to managed services.
- Move media and MLflow artifacts to object storage.
- Put web static assets behind a CDN.
- Add central logs, metrics, and alerting for job failures and latency.
