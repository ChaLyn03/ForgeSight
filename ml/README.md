# ML folder

Place datasets, training scripts and configs here.

## Baseline training and MLflow model registration

This repository includes a baseline training script for MLflow model registration:

- `ml/train_baseline.py`

### Run locally

Install the repo virtual environment dependencies first and run the script from there:

```bash
# From the ForgeSight repo root
./.venv/bin/python -m pip install -r apps/api/requirements-ml.txt
./.venv/bin/python ml/train_baseline.py \
  --tracking-uri http://localhost:5000 \
  --experiment forgesight-baseline \
  --model-name forgesight-inspection-model \
  --model-stage Production
```

### Docker Compose

When running with Docker Compose, the MLflow server is available at `http://localhost:5000`.
Compose mounts `./ml/artifacts` into MLflow, API, and worker containers at `/mlflow/artifacts` so registered models are available to inference workers.

```bash
docker compose exec api python /app/ml/train_baseline.py \
  --tracking-uri http://mlflow:5000 \
  --experiment forgesight-baseline \
  --model-name forgesight-inspection-model \
  --model-stage Production
```

The script logs a PyTorch model to MLflow, saves an ONNX artifact, and registers the model under `forgesight-inspection-model`.
