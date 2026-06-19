from forgesight_api.ml.model import ModelLoader


def test_model_loader_falls_back_when_no_tracking_uri(monkeypatch):
    ModelLoader._instances.clear()
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.delenv("MLFLOW_MODEL_URI", raising=False)
    monkeypatch.delenv("MLFLOW_MODEL_NAME", raising=False)
    monkeypatch.delenv("MLFLOW_MODEL_STAGE", raising=False)

    model = ModelLoader.get_model()

    assert model.flavor == "stub"
    assert model.model is None


def test_model_loader_resolves_model_uri_by_stage(monkeypatch):
    ModelLoader._instances.clear()
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    monkeypatch.setenv("MLFLOW_MODEL_NAME", "forgesight-inspection-model")
    monkeypatch.setenv("MLFLOW_MODEL_STAGE", "Staging")
    monkeypatch.setenv("MLFLOW_MODEL_URI", "models:/forgesight-inspection-model/Staging")
    monkeypatch.setenv("MLFLOW_DISABLE_MODEL_LOAD", "1")

    model = ModelLoader.get_model()

    assert model.model_uri == "models:/forgesight-inspection-model/Staging"
