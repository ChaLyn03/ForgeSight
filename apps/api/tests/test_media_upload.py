import os
from io import BytesIO

from PIL import Image

from conftest import ASGITestClient


def make_test_image_bytes(format: str = "PNG") -> bytes:
    buf = BytesIO()
    img = Image.new("RGB", (16, 16), color=(255, 0, 0))
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


def test_upload_media(tmp_path, monkeypatch):
    # configure a fresh sqlite DB and media root
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    media_root = tmp_path / "media"
    monkeypatch.setenv("MEDIA_ROOT", str(media_root))

    # import app after setting env
    from forgesight_api import manage
    from forgesight_api.db.session import SessionLocal
    from forgesight_api.db.models import Inspection
    from forgesight_api.main import app

    # create tables
    manage.create_tables()

    client = ASGITestClient(app)

    # register and login
    client.post("/api/v1/auth/register", json={"email": "u1@example.com", "password": "pass", "display_name": "U1", "role": "inspector"})
    r = client.post("/api/v1/auth/login", json={"email": "u1@example.com", "password": "pass"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create an inspection record
    session = SessionLocal()
    insp = Inspection(component_type="test", part_identifier="p1")
    session.add(insp)
    session.commit()
    session.refresh(insp)
    session.close()

    img_bytes = make_test_image_bytes("PNG")
    files = [("files", ("test.png", BytesIO(img_bytes), "image/png"))]

    resp = client.post(f"/api/v1/inspections/{insp.id}/media", files=files, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert item["inspection_id"] == insp.id

    # check file exists (storage_key may be absolute or repo-relative)
    storage_key = item["storage_key"]
    if os.path.isabs(storage_key):
        storage_path = storage_key
    else:
        storage_path = os.path.join(os.getcwd(), storage_key)
    assert os.path.exists(storage_path)
