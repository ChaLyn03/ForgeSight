from io import BytesIO

from PIL import Image

from conftest import ASGITestClient


def make_test_image_bytes(format: str = "PNG") -> bytes:
    buf = BytesIO()
    img = Image.new("RGB", (32, 32), color=(0, 255, 0))
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


def test_inference_job_flow(tmp_path, monkeypatch):
    # configure environment for test: sqlite db, media root, force sync processing
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("FORCE_SYNC_INFERENCE", "1")
    monkeypatch.setenv("MLFLOW_DISABLE_MODEL_LOAD", "1")

    from forgesight_api import manage
    from forgesight_api.main import app
    from forgesight_api.db.session import SessionLocal
    from forgesight_api.db.models import Inspection, InferenceJob, InferenceResult

    manage.create_tables()

    client = ASGITestClient(app)

    # register/login
    client.post("/api/v1/auth/register", json={"email": "i1@example.com", "password": "pass", "display_name": "I1", "role": "inspector"})
    r = client.post("/api/v1/auth/login", json={"email": "i1@example.com", "password": "pass"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create inspection
    session = SessionLocal()
    insp = Inspection(component_type="test", part_identifier="p1")
    session.add(insp)
    session.commit()
    session.refresh(insp)
    session.close()

    # upload media
    img_bytes = make_test_image_bytes()
    files = [("files", ("test.png", BytesIO(img_bytes), "image/png"))]
    resp = client.post(f"/api/v1/inspections/{insp.id}/media", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1

    # create job and force synchronous processing via env var
    payload = {"inspection_id": insp.id}
    r = client.post("/api/v1/inference/jobs", json=payload, headers=headers)
    assert r.status_code == 200
    job_meta = r.json()
    assert "id" in job_meta
    assert job_meta["status"] == "completed"

    r = client.get(f"/api/v1/inference/jobs/{job_meta['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    r = client.get(f"/api/v1/inference/results/{job_meta['id']}", headers=headers)
    assert r.status_code == 200
    result_meta = r.json()
    assert result_meta["job_id"] == job_meta["id"]
    assert result_meta["overlay_url"].startswith("/media/")

    # verify DB has results
    session = SessionLocal()
    job = session.query(InferenceJob).filter_by(id=job_meta["id"]).one()
    assert job.status == "completed"
    results = session.query(InferenceResult).filter_by(job_id=job.id).all()
    assert len(results) >= 1
    session.close()
