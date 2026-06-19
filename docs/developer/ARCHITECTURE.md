# ForgeSight Architecture

## System Overview

ForgeSight is an AI-assisted visual inspection platform with the following architecture:

```
┌─────────────────────────────────────────────────────────┐
│                     Web Browser (React)                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Dashboard │ Upload │ Results │ Model Registry      │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (8000)                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Inspections │ Media Upload │ Inference │ Models       │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           SQLAlchemy ORM (Database Models)            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ Queue
                       ▼
┌──────────────────────────────────────────────────────────────┐
│               Dramatiq Worker (async)                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │    Inference Job Processing (ML Model Loading)        │  │
│  │    ├─ Fetch image from media store                    │  │
│  │    ├─ Load model from MLflow                          │  │
│  │    ├─ Run inference (PyTorch/ONNX)                    │  │
│  │    └─ Generate overlays & segmentation               │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
       ┌──────────────┬─────────────┬────────────────┐
       ▼              ▼             ▼                ▼
   PostgreSQL      Redis        MLflow          Media
   (database)    (broker)     (registry)       Storage
```

## Components

### 1. Web Frontend (React + Vite)

**Location:** `apps/web/`

**Responsibilities:**
- User interface for inspection submission
- Real-time result viewing
- Model registry browser
- Inspection history/dashboard

**Key Technologies:**
- React 18
- TypeScript
- Axios (HTTP client)
- CSS3 (responsive design)

**Pages:**
- `InspectionList` — Browse all inspections
- `InspectionUpload` — Submit new inspection with image
- `ResultViewer` — View inference result with overlays
- `ModelManagement` — Browse MLflow registry, transition stages

---

### 2. FastAPI Backend

**Location:** `apps/api/forgesight_api/`

**Responsibilities:**
- RESTful API for inspections, media, inference, models
- Database ORM (SQLAlchemy)
- Authentication (JWT)
- Orchestrate inference jobs (enqueue to worker)
- MLflow integration (query registry, transition stages)

**Routes:**

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/v1/auth/register` | POST | Create user account |
| `/api/v1/auth/login` | POST | Issue JWT |
| `/api/v1/inspections` | POST | Create inspection |
| `/api/v1/inspections` | GET | List inspections |
| `/api/v1/inspections/{id}/media` | POST | Upload image |
| `/api/v1/inference/jobs` | POST | Submit inference job |
| `/api/v1/inference/jobs/{id}` | GET | Check job status |
| `/api/v1/inference/inspections/{id}/jobs/latest` | GET | Get latest job for an inspection |
| `/api/v1/inference/results/{id}` | GET | Get inference result |
| `/api/v1/models/registry` | GET | List MLflow models |
| `/api/v1/models/transition-stage` | POST | Change model stage |

**Key Files:**
- `main.py` — FastAPI app entry
- `routes/*.py` — API endpoints
- `db/models.py` — SQLAlchemy models
- `ml/model.py` — Model loader with fallback inference
- `worker/worker.py` — Job processing logic

---

### 3. Dramatiq Worker

**Location:** `apps/worker/`

**Responsibilities:**
- Process inference jobs asynchronously
- Load ML model from MLflow
- Run inference on image
- Generate detection overlays & segmentation masks
- Update job status in database

**Flow:**
```
1. Backend enqueues job → Redis broker
2. Worker polls Redis for jobs
3. Worker fetches image from media store
4. Worker loads model from MLflow (with fallback)
5. Worker runs inference
6. Worker saves results to database
7. Worker updates job status to "completed"
```

**Key Files:**
- `forgesight_api/worker/worker.py` — Dramatiq actor and core processing logic
- `forgesight_worker/tasks.py` — Thin worker package entrypoint

---

### 4. Database (PostgreSQL)

**Responsibilities:**
- Persistent storage for inspections, jobs, results
- User authentication data

**Tables:**
- `inspections` — Inspection records (component_type, part_id, etc.)
- `media_files` — Uploaded image metadata
- `inference_jobs` — Job records (status, timing)
- `inference_results` — Prediction results (label, confidence, overlay keys)
- `users` — User accounts

---

### 5. Message Broker (Redis)

**Responsibilities:**
- Queue for async inference jobs (Dramatiq broker)
- Job state management

**Usage:**
```
FastAPI → Redis (enqueue job) → Dramatiq Worker
```

---

### 6. MLflow Registry

**Responsibilities:**
- Store trained models (PyTorch, ONNX)
- Manage versions & stages (Production, Staging, Archived)
- Track experiments (hyperparameters, metrics)
- Store local artifacts under `/mlflow/artifacts`, shared with API and worker containers through `./ml/artifacts`

**Model Lifecycle:**
```
1. Train baseline model (ml/train_baseline.py)
2. Log to MLflow (torch, ONNX artifacts)
3. Register model version
4. Transition to stage (Production by default)
5. Worker loads from registry during inference
```

**URL:** http://localhost:5000 (UI for browsing)

---

### 7. Media Storage

**Responsibilities:**
- Store uploaded inspection images
- Serve media files (via FastAPI static mount)

**Location:** `./storage/` (local) or volume-mounted in Docker

**Files:**
- Original images (PNG, JPG)
- Processed overlays (PNG)
- Segmentation masks (PNG)

---

## Data Flow: From Upload to Result

### 1. User Submits Inspection

```
Frontend → POST /api/v1/inspections → Backend
          ↓
        Create inspection record in DB
```

### 2. User Uploads Image

```
Frontend → POST /api/v1/inspections/{id}/media → Backend
          ↓
        Save image to storage/
        Create media_file record
```

### 3. User Submits for Inference

```
Frontend → POST /api/v1/inference/jobs → Backend
          ↓
        Create inference_job (status: "queued")
        Enqueue job to Redis
```

### 4. Worker Processes Job

```
Dramatiq Worker
  1. Fetch job from Redis
  2. Fetch image from storage/
  3. Load model from MLflow (or fallback to synthetic)
  4. Run inference on image
  5. Generate overlays & segmentation
  6. Save result to inference_result table
  7. Update job status to "completed"
```

### 5. Frontend Polls & Displays

```
Frontend → GET /api/v1/inference/jobs/{id}
          ↓
        Check status (polling every 2 seconds)
        When "completed":
  → GET /api/v1/inference/results/{id}
          ↓
        Display prediction, confidence, overlays
```

---

## Model Loading & Inference

### MLflow Integration

```python
# During inference (worker/worker.py)
import mlflow

# Resolve model URI from stage/name
model_uri = f"models:/forgesight-inspection-model/Production"

# Try MLflow pyfunc first
model = mlflow.pyfunc.load_model(model_uri)

# Fallback to PyTorch
model = mlflow.pytorch.load_model(model_uri)

# Fallback to a downloaded ONNX artifact via onnxruntime
session = onnxruntime.InferenceSession("model.onnx")

# Last resort: synthetic inference
prediction = random_prediction()
```

### Inference Pipeline

```
Image (bytes)
  ↓
  ├─ PIL.Image.open() + normalize
  ├─ PyTorch tensor or ONNX input format
  ├─ Model inference
  ├─ Post-process predictions (argmax, softmax)
  ↓
Detection overlay (PNG)
  ├─ Draw bounding box if defect
  ├─ Alpha blend with original
  ↓
Segmentation mask (PNG)
  ├─ Binary mask (255 for defect regions)
  ↓
Result (JSON)
  {
    "predicted_label": "defect" | "ok",
    "confidence": 50-100,
    "overlay": <PNG bytes>,
    "segmentation": <PNG bytes>,
    "latency_ms": <milliseconds>
  }
```

---

## Fallback Strategies

### Model Not Available

```
1. Try PyTorch format (MLflow native)
2. Try ONNX format (via onnxruntime)
3. Use synthetic prediction (random 50% defect, random confidence)
```

### MLflow Registry Unavailable

```
1. Load from local cache (if previously loaded)
2. Return synthetic result
```

---

## Deployment Architecture

### Docker Compose (Local/Dev)

```yaml
services:
  postgres   -> database, internal Compose network
  redis      -> broker, internal Compose network
  mlflow     -> model registry, published on localhost:5000
  api        -> FastAPI backend, published on localhost:8000
  worker     -> Dramatiq worker
  web        -> React frontend, published on localhost:3000, proxies API/media

shared paths:
  media volume        -> uploaded images and derived result assets
  ./ml/artifacts      -> MLflow model artifacts mounted at /mlflow/artifacts
```

### Production (Recommended)

```
Kubernetes/ECS/Heroku/Railway
  ├─ API (FastAPI, replicated)
  ├─ Worker (Dramatiq, replicated)
  ├─ Frontend (React static, CDN)
  ├─ PostgreSQL (managed RDS/Cloud SQL)
  ├─ Redis (managed ElastiCache/MemoryStore)
  └─ MLflow (managed, or self-hosted)
```

---

## Security Considerations

1. **Authentication** — JWT tokens required for most endpoints
2. **Database** — Credentials in environment variables, not committed
3. **Media Upload** — File type validation, virus scan (optional)
4. **CORS** — Enabled for frontend origin
5. **Secrets** — Use .env or secrets manager (not in code)

---

## Performance Optimizations

1. **Model Caching** — ModelLoader caches loaded models in memory
2. **Async Processing** — Inference via Dramatiq worker (non-blocking)
3. **Database Indices** — On inspection_id, job_id for queries
4. **Frontend Polling** — Polls every 2s (adjustable)
5. **Overlay Caching** — Overlay and segmentation PNGs are saved in media storage and referenced by URL

---

## Monitoring & Observability

### Logs

```bash
# Backend
docker compose logs -f api

# Worker
docker compose logs -f worker

# MLflow
docker compose logs -f mlflow
```

### Health Checks

```
GET /health/live   → liveness
GET /health/ready  → readiness with database check
```

### Metrics (Optional)

- Inference latency (latency_ms)
- Job success rate (via inference_result.status)
- Model accuracy (manual annotation in frontend)

---

## Future Enhancements

1. **Review Workflow** — Approve/reject predictions with feedback
2. **Active Learning** — Retrain on human-corrected examples
3. **Multi-Model Ensembling** — Combine predictions from multiple models
4. **Real-time Alerts** — Notify users of defects
5. **Analytics Dashboard** — Trends, defect hotspots, model performance
6. **Custom Model Training** — Fine-tune baseline on user data
7. **Batch Processing** — Process multiple images in parallel
8. **Explainability** — Attention maps, saliency visualizations

---

## References

- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Dramatiq Docs:** https://dramatiq.io
- **MLflow Docs:** https://mlflow.org
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org
- **React Docs:** https://react.dev
