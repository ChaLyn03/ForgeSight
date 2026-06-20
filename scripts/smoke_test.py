#!/usr/bin/env python3
"""End-to-end ForgeSight deployment smoke test."""

from __future__ import annotations

import io
import os
import time
import uuid
from urllib.parse import urljoin

import requests
from PIL import Image


API_BASE = os.getenv("FORGESIGHT_API_BASE", "http://127.0.0.1:8000/api/v1").rstrip("/")
REQUEST_TIMEOUT = int(os.getenv("FORGESIGHT_REQUEST_TIMEOUT", "10"))
JOB_TIMEOUT = int(os.getenv("FORGESIGHT_JOB_TIMEOUT", "90"))
POLL_SECONDS = float(os.getenv("FORGESIGHT_POLL_SECONDS", "2"))


def _health_url() -> str:
    configured = os.getenv("FORGESIGHT_HEALTH_URL")
    if configured:
        return configured
    if API_BASE.endswith("/api/v1"):
        return API_BASE[: -len("/api/v1")] + "/health/ready"
    return urljoin(API_BASE + "/", "../health/ready")


def _request(method: str, url: str, **kwargs) -> requests.Response:
    response = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
    response.raise_for_status()
    return response


def _make_image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color=(0, 255, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    print(f"health GET {_health_url()}")
    _request("GET", _health_url())

    email = f"smoke-{uuid.uuid4().hex[:10]}@example.com"
    password = "pass12345"

    register = _request(
        "POST",
        f"{API_BASE}/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "Smoke",
            "role": "inspector",
        },
    )
    print(f"register {register.status_code}")

    login = _request("POST", f"{API_BASE}/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"login {login.status_code}")

    inspection = _request(
        "POST",
        f"{API_BASE}/inspections",
        json={"component_type": "sensor", "part_identifier": "SMOKE-DEPLOY"},
        headers=headers,
    )
    inspection_id = inspection.json()["id"]
    print(f"inspection {inspection_id}")

    upload = _request(
        "POST",
        f"{API_BASE}/inspections/{inspection_id}/media",
        files={"files": ("smoke.png", _make_image_bytes(), "image/png")},
        headers=headers,
    )
    media = upload.json()
    if not media:
        raise AssertionError("media upload returned no media records")
    print(f"upload {media[0]['id']}")

    job_response = _request(
        "POST",
        f"{API_BASE}/inference/jobs",
        json={"inspection_id": inspection_id},
        headers=headers,
    )
    job_id = job_response.json()["id"]
    print(f"job {job_id}")

    deadline = time.monotonic() + JOB_TIMEOUT
    job = job_response.json()
    while time.monotonic() < deadline:
        job = _request("GET", f"{API_BASE}/inference/jobs/{job_id}", headers=headers).json()
        print(f"job_status {job['status']}")
        if job["status"] in {"completed", "failed"}:
            break
        time.sleep(POLL_SECONDS)

    if job["status"] != "completed":
        raise AssertionError(f"inference job did not complete: {job}")

    result = _request("GET", f"{API_BASE}/inference/results/{job_id}", headers=headers).json()
    if not result.get("overlay_url") or not result.get("segmentation_url"):
        raise AssertionError(f"result missing generated media URLs: {result}")

    print(
        "smoke_ok "
        f"inspection_id={inspection_id} "
        f"job_id={job_id} "
        f"label={result.get('predicted_label')} "
        f"confidence={result.get('confidence')}"
    )


if __name__ == "__main__":
    main()
