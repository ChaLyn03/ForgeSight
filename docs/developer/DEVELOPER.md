# ForgeSight Developer Guide

## Quick Start

### Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 20+** (for frontend)
- **Docker & Docker Compose** (optional, for full stack)
- **Git**

### Local Development

#### 1. Clone & Setup Python Environment

```bash
git clone https://github.com/forgesight/forgesight.git
cd ForgeSight

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies, including ML/runtime extras
make setup
```

#### 2. Setup Database & Run Tests

```bash
# From the ForgeSight root directory
cd apps/api

# Create SQLite database tables for local-only development
python manage.py

# Run tests
../../.venv/bin/python -m pytest -q
```

#### 3. Run Backend (FastAPI)

```bash
cd apps/api
uvicorn forgesight_api.main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

API docs: `http://localhost:8000/docs`

#### 4. Run Frontend (React + Vite)

In a new terminal:

```bash
cd apps/web

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be available at `http://localhost:3000`

#### 5. Run Worker (Dramatiq)

For full-stack development, prefer Docker Compose. If you run the worker locally, use a locally reachable Redis instance because the Compose Redis service is not published to the host by default:

```bash
# From the repo root
redis-server

export PYTHONPATH="$PWD/apps/api:$PWD/apps/worker"
export DATABASE_URL=sqlite:///apps/api/dev.db
export REDIS_URL=redis://localhost:6379/0
.venv/bin/python -m dramatiq forgesight_api.worker.worker -p 4
```

For local API-only work without Redis, set `FORCE_SYNC_INFERENCE=1` so inference jobs run inline.

---

## Docker Compose (Full Stack)

### Build & Run

```bash
docker compose up --build
```

Services will be available at:
- **API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **MLflow**: http://localhost:5000
- **Postgres**: internal Compose network only; use `docker compose exec postgres psql -U forgesight -d forgesight`
- **Redis**: internal Compose network only; use `docker compose exec redis redis-cli`

The Compose stack mounts `./ml/artifacts` into MLflow, API, and worker containers at `/mlflow/artifacts`. This is required because the local MLflow artifact store returns filesystem artifact URIs that the training process and worker both need to read.

### Useful Docker Commands

```bash
# View logs
docker compose logs -f api

# Verify deployed workflow
make smoke

# Run command in running container
docker compose exec api python manage.py

# Restart specific service
docker compose restart worker

# Remove all containers & volumes
docker compose down -v
```

---

## ML Baseline Training

### Local Training (with MLflow)

The baseline training script requires MLflow. You can run it locally or with Docker Compose.

**Option 1: Local (requires MLflow server running)**

```bash
# Start MLflow server (if not in Docker Compose)
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./ml/artifacts

# In another terminal, use the repo venv:
./.venv/bin/python -m pip install -r apps/api/requirements-ml.txt
./.venv/bin/python ml/train_baseline.py \
  --tracking-uri http://localhost:5000 \
  --experiment forgesight-baseline \
  --model-name forgesight-inspection-model \
  --model-stage Production
```

**Option 2: Via Docker Compose**

```bash
# Start full stack
docker compose up -d

# Train in the api container
docker compose exec api python /app/ml/train_baseline.py \
  --tracking-uri http://mlflow:5000 \
  --experiment forgesight-baseline \
  --model-name forgesight-inspection-model \
  --model-stage Production
```

After training, view models at: **http://localhost:5000** (MLflow UI)

---

## Project Structure

```
ForgeSight/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── forgesight_api/
│   │   │   ├── main.py        # FastAPI app entry
│   │   │   ├── routes/        # API endpoints (inspections, inference, models, etc.)
│   │   │   ├── db/            # SQLAlchemy models & session
│   │   │   ├── ml/            # ML model loader & inference
│   │   │   ├── worker/        # Core inference worker logic and Dramatiq actor
│   │   │   └── auth.py        # Authentication (JWT)
│   │   ├── requirements-dev.txt
│   │   ├── requirements-ml.txt
│   │   ├── tests/             # Pytest test suite
│   │   └── Dockerfile
│   ├── web/                    # React + Vite frontend
│   │   ├── src/
│   │   │   ├── main.tsx       # Entry point
│   │   │   ├── App.tsx        # Main app component
│   │   │   ├── api.ts         # API client & types
│   │   │   ├── pages/         # Page components
│   │   │   └── styles/        # CSS styles
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   └── Dockerfile
│   └── worker/                # Dramatiq worker
│       ├── forgesight_worker/
│       │   └── tasks.py       # Thin worker package entrypoint
│       └── pyproject.toml
├── ml/
│   ├── train_baseline.py      # Baseline training script
│   ├── artifacts/             # MLflow artifacts (models, ONNX)
│   └── README.md
├── docs/
│   ├── developer/             # This guide
│   └── architecture/          # Architecture docs
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI
└── README.md
```

---

## API Overview

### Authentication

Authentication uses JWT tokens. Most endpoints require a valid token via `Authorization: Bearer <token>` header.

### Key Endpoints

#### Inspections
- `POST /api/v1/inspections` — Create inspection
- `GET /api/v1/inspections` — List inspections
- `GET /api/v1/inspections/{id}` — Get inspection details

#### Media Upload
- `POST /api/v1/inspections/{id}/media` — Upload image file

#### Inference
- `POST /api/v1/inference/jobs` — Submit inference job
- `GET /api/v1/inference/jobs/{id}` — Get job status
- `GET /api/v1/inference/inspections/{id}/jobs/latest` — Get latest job for an inspection
- `GET /api/v1/inference/results/{id}` — Get inference result

#### Models
- `GET /api/v1/models/registry` — List registered MLflow models
- `POST /api/v1/models/transition-stage` — Transition model version to stage

#### Health
- `GET /health/live` — Liveness check
- `GET /health/ready` — Readiness check

See API docs at `http://localhost:8000/docs` (Swagger UI)

---

## Testing

### Run All Tests

```bash
make test
```

### Run Specific Test

```bash
pytest tests/test_inference_job.py::test_inference_job_flow -v
```

### Run with Coverage

```bash
pytest --cov=forgesight_api --cov-report=html
```

### Frontend Tests

```bash
cd apps/web
npm test -- --run --passWithNoTests
```

### Deployment Smoke

```bash
make smoke
```

The smoke test uses `scripts/smoke_test.py` and expects the API to be available at `FORGESIGHT_API_BASE` or `http://127.0.0.1:8000/api/v1`.

---

## Environment Variables

### Backend (`.env` or `docker-compose.yml`)

```bash
# Database
DATABASE_URL=postgresql://forgesight:forgesight@postgres:5432/forgesight

# Redis (for Dramatiq broker)
REDIS_URL=redis://redis:6379/0

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_EXPERIMENT_NAME=forgesight-baseline
MLFLOW_MODEL_NAME=forgesight-inspection-model
MLFLOW_MODEL_STAGE=Production

# Media storage
MEDIA_ROOT=./storage

# Force synchronous inference (for testing)
FORCE_SYNC_INFERENCE=0

# Auth and CORS
SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Frontend (`.env.local` or `docker-compose.yml`)

```bash
VITE_API_URL=/api/v1
VITE_API_PROXY_TARGET=http://localhost:8000
```

---

## Common Development Tasks

### Add a New API Endpoint

1. Create a new route file in `apps/api/forgesight_api/routes/`
2. Define route handlers with Pydantic models
3. Import and register the router in `main.py`

Example:
```python
# routes/custom.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/custom", tags=["custom"])

@router.get("/data")
async def get_data():
    return {"data": "value"}
```

Register in `main.py`:
```python
from forgesight_api.routes.custom import router as custom_router
app.include_router(custom_router, prefix="/api/v1")
```

### Add a New React Page

1. Create component in `apps/web/src/pages/MyPage.tsx`
2. Add to navigation in `src/App.tsx`
3. Create styles in `src/styles/MyPage.css`

Example:
```typescript
// pages/MyPage.tsx
import React from 'react'
import '../styles/MyPage.css'

export default function MyPage() {
  return <div className="container"><h1>My Page</h1></div>
}
```

Update `App.tsx`:
```typescript
import MyPage from './pages/MyPage'
// Add to page type: type Page = 'list' | 'upload' | 'result' | 'models' | 'mypage'
// Add nav button and render component
```

### Update Database Schema

1. Modify model in `apps/api/forgesight_api/db/models.py`
2. Generate Alembic migration:
```bash
cd apps/api
alembic revision --autogenerate -m "Add new column"
```
3. Apply migration:
```bash
alembic upgrade head
```

---

## Troubleshooting

### Frontend can't connect to API

- Ensure backend is running on `http://localhost:8000`
- In local Vite dev, keep `VITE_API_URL=/api/v1` and set `VITE_API_PROXY_TARGET=http://localhost:8000`
- In Docker, use the default Nginx proxy for `/api` and `/media`

### Tests fail with "ModuleNotFoundError"

- Ensure you're using the repo venv: `source .venv/bin/activate`
- Install dev dependencies: `pip install -r apps/api/requirements-dev.txt`

### Worker not processing jobs

- Check Redis is running: `docker compose exec redis redis-cli ping` should return "PONG"
- Verify `REDIS_URL` environment variable
- Check worker logs for errors

### MLflow not loading models

- Ensure `MLFLOW_TRACKING_URI` is set correctly
- Check MLflow server is running
- Verify model exists in registry
- In Docker Compose, verify `./ml/artifacts` is mounted into the API and worker containers at `/mlflow/artifacts`

---

## CI/CD Pipeline

GitHub Actions runs on every push/PR:

1. **Backend lint** — Check API and ML code with `ruff`
2. **Backend test** — Run the pytest suite
3. **Frontend build** — Install with `npm ci` and run Vite production build
4. **Frontend audit** — Run `npm audit --audit-level=high`

The separate Compose smoke workflow can be run manually and runs on pushes to `main` that touch deploy-relevant files. It builds the stack and executes `scripts/smoke_test.py`.

See `.github/workflows/ci.yml` and `.github/workflows/compose-smoke.yml` for details.

---

## Next Steps

- See [Architecture Overview](../architecture/overview.md) for system design
- See [Production Deployment](../deployment/PRODUCTION.md) for release planning
- See [ML README](../../ml/README.md) for ML details
- See [Frontend README](../../apps/web/README.md) for UI components
