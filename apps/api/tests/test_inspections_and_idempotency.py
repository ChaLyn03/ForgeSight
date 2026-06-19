from io import BytesIO

from PIL import Image

from conftest import ASGITestClient


def make_test_image_bytes(format: str = "PNG") -> bytes:
    buf = BytesIO()
    img = Image.new("RGB", (16, 16), color=(0, 255, 0))
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


def test_create_inspection_and_list(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))

    from forgesight_api import manage
    from forgesight_api.main import app

    manage.create_tables()

    client = ASGITestClient(app)

    # register/login
    client.post("/api/v1/auth/register", json={"email": "u2@example.com", "password": "pass", "display_name": "U2", "role": "inspector"})
    r = client.post("/api/v1/auth/login", json={"email": "u2@example.com", "password": "pass"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"component_type": "widget", "part_identifier": "X123"}
    resp = client.post("/api/v1/inspections", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["component_type"] == "widget"
    assert "id" in data

    # list inspections
    resp = client.get("/api/v1/inspections", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["id"] == data["id"] for i in items)


def test_idempotent_upload(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    media_root = tmp_path / "media"
    monkeypatch.setenv("MEDIA_ROOT", str(media_root))

    from forgesight_api import manage
    from forgesight_api.db.session import SessionLocal
    from forgesight_api.db.models import Inspection, MediaFile
    from forgesight_api.main import app

    manage.create_tables()

    session = SessionLocal()
    insp = Inspection(component_type="test", part_identifier="p1")
    session.add(insp)
    session.commit()
    session.refresh(insp)
    session.close()

    client = ASGITestClient(app)

    # login
    r = client.post("/api/v1/auth/login", json={"email": "u2@example.com", "password": "pass"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    img_bytes = make_test_image_bytes()
    files = [("files", ("a.png", BytesIO(img_bytes), "image/png"))]

    resp1 = client.post(f"/api/v1/inspections/{insp.id}/media", files=files, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()[0]

    # upload same bytes again
    resp2 = client.post(f"/api/v1/inspections/{insp.id}/media", files=files, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()[0]

    # should reference same media record
    assert data1["sha256"] == data2["sha256"]
    assert data1["id"] == data2["id"]

    # DB should have only one media entry for this inspection
    session = SessionLocal()
    count = session.query(MediaFile).filter(MediaFile.inspection_id == insp.id).count()
    session.close()
    assert count == 1
