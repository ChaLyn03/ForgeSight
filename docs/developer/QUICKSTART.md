# ForgeSight Quick Start

Time to first inspection: about 5 minutes once Docker images are built.

## Step 1: Start the Stack (Docker Compose)

```bash
# From ForgeSight root
cp .env.example .env
# Set SECRET_KEY in .env before non-local use
docker compose up --build
```

Compose runs API migrations before starting the API. Wait for the services to become healthy:

```bash
docker compose ps
curl -fsS http://localhost:8000/health/ready
curl -fsS http://localhost:5000/health
```

Published endpoints:

- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs
- MLflow UI: http://localhost:5000

PostgreSQL and Redis are available inside the Compose network. Access them with `docker compose exec postgres ...` and `docker compose exec redis ...`.

MLflow artifacts are stored under `./ml/artifacts` and mounted into MLflow, API, and worker containers. Keep that directory when you want registered local models to remain loadable.

## Step 2: Register a Baseline Model (Optional)

The inspection workflow works before a model is registered because the worker falls back to synthetic inference. Register the baseline model when you want MLflow-backed model loading and a populated Models tab.

```bash
docker compose exec api python /app/ml/train_baseline.py \
  --tracking-uri http://mlflow:5000 \
  --experiment forgesight-baseline \
  --model-name forgesight-inspection-model \
  --model-stage Production
```

Expected shape of output:

```
Epoch 1: train_loss=0.6934 val_acc=0.5000
...
Baseline training complete.
Model registered as: forgesight-inspection-model
```

View the registered model in MLflow at http://localhost:5000.

## Step 3: Open ForgeSight Web UI

Open **http://localhost:3000** in your browser.

You should see the ForgeSight dashboard with:

- **Inspections**
- **New Inspection**
- **Models**

## Step 4: Submit Your First Inspection

1. Register an account or sign in
2. Open **New Inspection**
3. Fill in a component type, part identifier, and image file
4. Submit the inspection

You should see:

```
Inspection submitted! Job ID: abc123...
```

## Step 5: View Results

1. Click **"Inspections"** tab
2. Click on the inspection card
3. You'll see:
   - **Status:** "running" to "completed"
   - **Prediction:** "ok" or "defect"
   - **Confidence:** 50-100%
   - **Detection overlay:** Red box if defect detected
   - **Segmentation mask:** Binary mask image

## Step 6: View & Manage Models

1. Click **"Models"** tab
2. Select a model from the left sidebar
3. See:
   - All versions
   - Current stages (Production, Staging, Archived)
   - Creation timestamps
4. **Promote/Archive** versions with buttons

---

## Useful Commands

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker
```

### Access Databases

```bash
# PostgreSQL
docker compose exec postgres psql -U forgesight -d forgesight

# Redis CLI
docker compose exec redis redis-cli
```

### Run Tests

```bash
make lint
make test
make audit
```

### Clean Everything

```bash
docker compose down -v  # removes all containers & volumes
```

---

## Typical Workflow

```
1. Start stack (docker compose up)
2. Optionally train baseline (`docker compose exec api python /app/ml/train_baseline.py`)
3. Open web UI (http://localhost:3000)
4. Submit inspection (New Inspection tab)
5. View result (Inspections tab)
6. Manage models (Models tab)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 3000/8000 already in use | `docker compose restart` or change ports in `docker-compose.yml` |
| Models tab shows "No Models" | Run training step, wait 30s, refresh page |
| Inspection stuck "running" | Check worker logs: `docker compose logs worker` |
| Images not showing in results | Ensure media upload completed successfully |
| Web gets 401 responses | Register/sign in again; expired tokens are cleared automatically |
| API returns database errors after old failed boot | Recreate local volumes with `docker compose down -v` and `docker compose up --build` |

---

## Next Steps

- See [DEVELOPER.md](./DEVELOPER.md) for full setup & development guide
- See [Architecture](../architecture/overview.md) for system design
- Train your own model: See [ml/README.md](../../ml/README.md)
