import io
import os
import time
import random
import logging
import warnings
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class ModelLoader:
    """Load a model from MLflow registry and run inference on inspection imagery."""

    _instances: dict[str, "ModelLoader"] = {}

    @classmethod
    def get_model(cls, model_uri: str | None = None, model_name: str | None = None, model_stage: str | None = None) -> "ModelLoader":
        resolved_uri = cls._resolve_model_uri(model_uri, model_name, model_stage)
        if resolved_uri is None:
            # fallback to a shared synthetic model instance
            resolved_uri = "__fallback__"

        if resolved_uri not in cls._instances:
            instance = cls()
            instance.model_uri = resolved_uri
            instance._load(resolved_uri)
            cls._instances[resolved_uri] = instance

        return cls._instances[resolved_uri]

    @classmethod
    def _resolve_model_uri(cls, model_uri: str | None, model_name: str | None, model_stage: str | None) -> str | None:
        if model_uri:
            if model_uri.startswith("models:") or model_uri.startswith("runs:"):
                return model_uri
            if model_uri.isdigit():
                model_name = model_name or os.getenv("MLFLOW_MODEL_NAME", "forgesight-inspection-model")
                return f"models:/{model_name}/{model_uri}"
            if "/" not in model_uri:
                model_name = model_name or os.getenv("MLFLOW_MODEL_NAME", "forgesight-inspection-model")
                return f"models:/{model_name}/{model_uri}"
            return model_uri

        tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if not tracking_uri:
            return None

        model_name = model_name or os.getenv("MLFLOW_MODEL_NAME", "forgesight-inspection-model")
        model_stage = model_stage or os.getenv("MLFLOW_MODEL_STAGE", "Production")
        return os.getenv("MLFLOW_MODEL_URI", f"models:/{model_name}/{model_stage}")

    def _load(self, model_uri: str | None):
        self.model = None
        self.flavor = "stub"
        self.model_uri = model_uri

        if model_uri is None or model_uri == "__fallback__":
            logger.info("MLflow model URI not configured; using fallback inference")
            return

        if os.getenv("MLFLOW_DISABLE_MODEL_LOAD", "0") == "1":
            logger.info("MLflow model loading disabled; using fallback inference for %s", model_uri)
            return

        tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        load_candidates = [model_uri]
        if tracking_uri:
            try:
                import mlflow

                mlflow.set_tracking_uri(tracking_uri)
                artifact_location = self._resolve_logged_model_artifact_location(mlflow, model_uri)
                if artifact_location and artifact_location not in load_candidates:
                    load_candidates.insert(0, artifact_location)
            except Exception as exc:  # pragma: no cover
                logger.warning("MLflow model URI resolution failed: %s", exc, exc_info=True)

        for candidate in load_candidates:
            try:
                import mlflow.pytorch as mlflow_pytorch

                logger.info("Loading MLflow PyTorch model from %s", candidate)
                self.model = mlflow_pytorch.load_model(candidate)
                self.flavor = "torch"
                logger.info("Loaded MLflow PyTorch model %s", candidate)
                return
            except Exception as exc:  # pragma: no cover
                logger.warning("MLflow PyTorch model load failed for %s: %s", candidate, exc, exc_info=True)

        for candidate in load_candidates:
            try:
                import mlflow

                logger.info("Loading MLflow pyfunc model from %s", candidate)
                self.model = mlflow.pyfunc.load_model(candidate)
                self.flavor = "pyfunc"
                logger.info("Loaded MLflow pyfunc model %s", candidate)
                return
            except Exception as exc:  # pragma: no cover
                logger.warning("MLflow pyfunc model load failed for %s: %s", candidate, exc, exc_info=True)

        for candidate in load_candidates:
            try:
                import mlflow
                import onnxruntime

                local_path = mlflow.artifacts.download_artifacts(candidate)
                local_path = Path(local_path)
                onnx_files = list(local_path.rglob("*.onnx"))
                if not onnx_files:
                    raise FileNotFoundError("No ONNX model artifact found")

                session = onnxruntime.InferenceSession(str(onnx_files[0]), providers=["CPUExecutionProvider"])
                self.model = session
                self.flavor = "onnx"
                logger.info("Loaded MLflow ONNX model %s", candidate)
                return
            except Exception as exc:  # pragma: no cover
                logger.warning("MLflow ONNX model load failed for %s: %s", candidate, exc, exc_info=True)

        logger.info("Falling back to synthetic inference behavior")

    def _resolve_logged_model_artifact_location(self, mlflow_module, model_uri: str | None) -> str | None:
        if not model_uri or not model_uri.startswith("models:/"):
            return None

        client = mlflow_module.tracking.MlflowClient()
        remainder = model_uri.removeprefix("models:/")
        if remainder.startswith("m-") and "/" not in remainder:
            return client.get_logged_model(remainder).artifact_location

        if "/" not in remainder:
            return None

        name, selector = remainder.rsplit("/", 1)
        if selector.isdigit():
            version = client.get_model_version(name, selector)
        else:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=FutureWarning, message=".*get_latest_versions.*")
                versions = client.get_latest_versions(name, [selector])
            if not versions:
                return None
            version = max(versions, key=lambda item: int(item.version))

        source = version.source
        if source and source.startswith("models:/m-"):
            model_id = source.removeprefix("models:/")
            return client.get_logged_model(model_id).artifact_location
        return source

    def _prepare_image(self, image_bytes: bytes) -> tuple[bytes, np.ndarray]:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        array = np.asarray(img).astype(np.float32) / 255.0
        return image_bytes, array

    def _interpret_prediction(self, prediction: Any) -> dict[str, Any]:
        label = "ok"
        confidence = 50
        if hasattr(prediction, "detach"):
            prediction = prediction.detach().cpu().numpy()
        if isinstance(prediction, dict):
            label = prediction.get("label") or prediction.get("predicted_label") or label
            confidence = int(prediction.get("confidence", confidence))
        elif hasattr(prediction, "to_numpy"):
            arr = prediction.to_numpy()
            if arr.size:
                confidence = int(float(arr.flat[-1]))
                label = "defect" if confidence >= 0.5 else "ok"
        elif isinstance(prediction, (list, tuple, np.ndarray)):
            arr = np.asarray(prediction)
            if arr.ndim == 0:
                confidence = int(float(arr))
                label = "defect" if confidence >= 0.5 else "ok"
            elif arr.ndim >= 1 and arr.size >= 2:
                scores = arr.reshape(-1, arr.shape[-1])[0]
                exp_scores = np.exp(scores - np.max(scores))
                probabilities = exp_scores / exp_scores.sum()
                class_index = int(np.argmax(probabilities))
                label = "defect" if class_index == 1 else "ok"
                confidence = int(float(probabilities[class_index]) * 100)
            elif arr.ndim == 1 and arr.size == 1:
                score = float(arr[0])
                confidence = int(score * 100 if 0 <= score <= 1 else score)
                label = "defect" if confidence >= 50 else "ok"
        elif isinstance(prediction, (str, bytes)):
            label = prediction.decode() if isinstance(prediction, bytes) else prediction
        return {"predicted_label": label, "confidence": confidence}

    def infer(self, image_bytes: bytes) -> dict:
        start = time.time()
        raw_bytes, image_array = self._prepare_image(image_bytes)

        if self.flavor == "pyfunc" and self.model is not None:
            try:
                import pandas as pd

                batch = np.expand_dims(image_array, axis=0)
                data = pd.DataFrame({"image": list(batch)})
                prediction = self.model.predict(data)
                metadata = self._interpret_prediction(prediction)
            except Exception as exc:  # pragma: no cover
                logger.warning("Pyfunc inference failed: %s", exc, exc_info=True)
                metadata = {"predicted_label": "ok", "confidence": 50}
        elif self.flavor == "torch" and self.model is not None:
            try:
                import torch

                batch = np.transpose(image_array, (2, 0, 1))[None]
                tensor = torch.from_numpy(batch).float()
                self.model.eval()
                with torch.no_grad():
                    output = self.model(tensor)
                metadata = self._interpret_prediction(output)
            except Exception as exc:  # pragma: no cover
                logger.warning("Torch inference failed: %s", exc, exc_info=True)
                metadata = {"predicted_label": "ok", "confidence": 50}
        elif self.flavor == "onnx" and self.model is not None:
            try:
                batch = np.transpose(image_array, (2, 0, 1))[None]
                input_name = self.model.get_inputs()[0].name
                output = self.model.run(None, {input_name: batch.astype(np.float32)})
                metadata = self._interpret_prediction(output[0])
            except Exception as exc:  # pragma: no cover
                logger.warning("ONNX inference failed: %s", exc, exc_info=True)
                metadata = {"predicted_label": "ok", "confidence": 50}
        else:
            defect = random.random() < 0.35
            metadata = {
                "predicted_label": "defect" if defect else "ok",
                "confidence": int(50 + random.random() * 50),
            }

        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        w, h = img.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        if metadata["predicted_label"] == "defect":
            box = [int(w * 0.1), int(h * 0.1), int(w * 0.6), int(h * 0.6)]
            draw.rectangle(box, outline=(255, 0, 0, 180), width=3)
        combined = Image.alpha_composite(img, overlay)
        buf = io.BytesIO()
        combined.save(buf, format="PNG")
        overlay_bytes = buf.getvalue()

        mask = Image.new("L", (w, h), 0)
        if metadata["predicted_label"] == "defect":
            mdraw = ImageDraw.Draw(mask)
            mbox = [int(w * 0.1), int(h * 0.1), int(w * 0.6), int(h * 0.6)]
            mdraw.rectangle(mbox, fill=255)
        mbuf = io.BytesIO()
        mask.save(mbuf, format="PNG")
        segmentation_bytes = mbuf.getvalue()

        metadata.update(
            {
                "overlay": overlay_bytes,
                "segmentation": segmentation_bytes,
                "latency_ms": int((time.time() - start) * 1000),
            }
        )
        return metadata
