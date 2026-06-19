import argparse
import os
import random
import warnings
from pathlib import Path

os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

import mlflow
import mlflow.pytorch
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset


class BaselineDefectClassifier(nn.Module):
    def __init__(self, in_channels: int = 3, num_classes: int = 2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(32 * 8 * 8, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def generate_image(defect: bool, size: tuple[int, int] = (32, 32)) -> np.ndarray:
    image = np.ones((3, size[0], size[1]), dtype=np.float32) * 0.25
    if defect:
        x0 = random.randint(6, 18)
        y0 = random.randint(6, 18)
        image[:, y0 : y0 + 8, x0 : x0 + 8] = 0.95
    else:
        image += np.random.uniform(-0.05, 0.05, size=image.shape).astype(np.float32)
    return np.clip(image, 0.0, 1.0)


def build_dataset(samples: int = 512) -> TensorDataset:
    images = []
    labels = []
    for i in range(samples):
        defect = i % 2 == 0
        images.append(generate_image(defect))
        labels.append(1 if defect else 0)
    x = torch.tensor(np.stack(images), dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.long)
    return TensorDataset(x, y)


def train(model: nn.Module, loader: DataLoader, optimizer: optim.Optimizer, criterion: nn.Module, device: torch.device) -> float:
    model.train()
    total_loss = 0.0
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        optimizer.zero_grad()
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total_loss += float(loss.detach().cpu()) * x.size(0)
    return total_loss / len(loader.dataset)


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.to(device)
            logits = model(x)
            predictions = logits.argmax(dim=-1)
            correct += int((predictions == y).sum())
    return correct / len(loader.dataset)


def create_model_wrapper(model: nn.Module) -> torch.nn.Module:
    return model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a ForgeSight ML baseline and register it in MLflow")
    parser.add_argument("--experiment", default=os.getenv("MLFLOW_EXPERIMENT_NAME", "forgesight-baseline"))
    parser.add_argument("--model-name", default=os.getenv("MLFLOW_MODEL_NAME", "forgesight-inspection-model"))
    parser.add_argument("--model-stage", default=os.getenv("MLFLOW_MODEL_STAGE", "Production"))
    parser.add_argument("--tracking-uri", default=os.getenv("MLFLOW_TRACKING_URI", "sqlite:///./mlflow.db"))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--artifact-dir", default=os.getenv("MLFLOW_ARTIFACT_ROOT", "./mlflow-artifacts"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment(args.experiment)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BaselineDefectClassifier().to(device)
    train_dataset = build_dataset(512)
    val_dataset = build_dataset(128)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)
    criterion = nn.CrossEntropyLoss()

    with mlflow.start_run() as run:
        for epoch in range(1, args.epochs + 1):
            train_loss = train(model, train_loader, optimizer, criterion, device)
            val_acc = evaluate(model, val_loader, device)
            print(f"Epoch {epoch}: train_loss={train_loss:.4f} val_acc={val_acc:.4f}")
            mlflow.log_metric("train_loss", train_loss, step=epoch)
            mlflow.log_metric("validation_accuracy", val_acc, step=epoch)

        mlflow.log_param("epochs", args.epochs)
        mlflow.log_param("batch_size", args.batch_size)
        mlflow.log_param("learning_rate", args.learning_rate)
        mlflow.log_param("tracking_uri", args.tracking_uri)

        dummy_input = torch.randn(1, 3, 32, 32, device=device)
        model_info = mlflow.pytorch.log_model(
            model,
            artifact_path="model",
            registered_model_name=args.model_name,
            input_example=dummy_input,
            serialization_format="pickle",
        )

        # Export an ONNX artifact for fallback loading via MLflow artifacts.
        export_dir = Path(args.artifact_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        onnx_path = export_dir / "model.onnx"
        torch.onnx.export(
            model,
            dummy_input,
            str(onnx_path),
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
            opset_version=17,
        )
        mlflow.log_artifact(str(onnx_path), artifact_path="onnx")

        client = mlflow.tracking.MlflowClient()
        registered_version = getattr(model_info, "registered_model_version", None)
        if registered_version is None:
            versions = client.search_model_versions(f"name='{args.model_name}'")
            run_versions = [version for version in versions if version.run_id == run.info.run_id]
            if run_versions:
                registered_version = max(run_versions, key=lambda version: int(version.version)).version

        if registered_version is not None:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=FutureWarning, message=".*transition_model_version_stage.*")
                client.transition_model_version_stage(
                    name=args.model_name,
                    version=registered_version,
                    stage=args.model_stage,
                    archive_existing_versions=True,
                )

        print("Baseline training complete.")
        print(f"Model registered as: {args.model_name}")
        print(f"MLflow run ID: {run.info.run_id}")
        print(f"Model stage: {args.model_stage}")


if __name__ == "__main__":
    main()
