import os
import io
import hashlib
import uuid
from pathlib import Path
from typing import Dict
from urllib.parse import quote
from PIL import Image


def get_media_root() -> Path:
    return Path(os.getenv("MEDIA_ROOT", os.path.join(os.getcwd(), "storage"))).resolve()


def _ensure_media_root() -> Path:
    p = get_media_root()
    p.mkdir(parents=True, exist_ok=True)
    return p


def media_url_for_storage_key(storage_key: str | None) -> str | None:
    if not storage_key:
        return None

    media_root = get_media_root()
    storage_path = Path(storage_key)
    candidates = [storage_path]
    if not storage_path.is_absolute():
        candidates.append((Path.cwd() / storage_path).resolve())
        candidates.append((media_root / storage_path).resolve())

    relative_path: Path | None = None
    for candidate in candidates:
        try:
            relative_path = candidate.resolve().relative_to(media_root)
            break
        except ValueError:
            continue

    if relative_path is None:
        relative_path = Path(storage_path.name)

    return "/media/" + quote(relative_path.as_posix())


def open_media_file(storage_key: str) -> bytes:
    """Open a stored media file and return its bytes.

    Accepts either an absolute path or a repo-relative storage_key as
    returned by `save_upload_file`.
    """
    p = Path(storage_key)
    if not p.is_absolute():
        cwd_path = Path.cwd() / storage_key
        media_path = get_media_root() / storage_key
        p = cwd_path if cwd_path.exists() else media_path
    with open(p, "rb") as f:
        return f.read()


def save_file_contents(contents: bytes) -> Dict:
    """Validate and save image bytes to local storage."""
    if not contents:
        raise ValueError("Empty file")

    # compute sha256
    sha256 = hashlib.sha256(contents).hexdigest()
    size = len(contents)

    # validate image via PIL - fully load to ensure decode
    try:
        img = Image.open(io.BytesIO(contents))
        img.load()
    except Exception as exc:
        raise ValueError(f"Cannot decode image: {exc}") from exc

    width, height = img.size

    # dimension safeguard
    max_dim = int(os.getenv("MAX_IMAGE_DIM", 10000))
    if width > max_dim or height > max_dim:
        raise ValueError("Image dimensions exceed allowed maximum")

    fmt = img.format or "PNG"
    ext = fmt.lower()
    if ext == "jpeg":
        ext = "jpg"

    # normalize image and strip metadata by re-saving via Pillow
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    data = buf.getvalue()

    storage_dir = _ensure_media_root()
    filename = f"{uuid.uuid4()}.{ext}"
    storage_path = storage_dir / filename

    with open(storage_path, "wb") as f:
        f.write(data)

    # recompute size after any re-encoding
    size = len(data)

    # Prefer returning a path relative to the repository root when possible,
    # but fall back to an absolute path if the media root is outside the cwd.
    try:
        storage_key = str(storage_path.relative_to(Path.cwd()))
    except Exception:
        storage_key = str(storage_path)

    return {
        "storage_key": storage_key,
        "width": width,
        "height": height,
        "file_size": size,
        "sha256": sha256,
        "original_extension": ext,
    }


async def save_upload_file(upload_file=None, contents: bytes | None = None) -> Dict:
    """Validate and save an uploaded file to local storage.

    Can accept either an UploadFile (read internally) or raw bytes via
    the `contents` parameter. Returns metadata: storage_key, width,
    height, file_size, sha256
    """
    if contents is None:
        if upload_file is None:
            raise ValueError("No data provided")
        contents = await upload_file.read()

    return save_file_contents(contents)
