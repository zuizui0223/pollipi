from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient


SECRET_HEADER = "X-Pollipi-Device-Secret"


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _client(monkeypatch, tmp_path: Path, *, device_secret: str | None = None) -> TestClient:
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    monkeypatch.setenv("POLLIPI_DEVICE_ID", "test-pollipi")
    monkeypatch.setenv("POLLIPI_DEVICE_NAME", "Test PolliPi")
    monkeypatch.delenv("POLLIPI_ENABLE_LEGACY_ROUTES", raising=False)
    if device_secret is None:
        monkeypatch.delenv("POLLIPI_DEVICE_SECRET", raising=False)
    else:
        monkeypatch.setenv("POLLIPI_DEVICE_SECRET", device_secret)
    _clear_server_modules()
    app_module = importlib.import_module("visit_monitor_server.app")
    return TestClient(app_module.create_app())


def test_fake_camera_scheduled_timelapse_smoke(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        device = client.get("/device")
        assert device.status_code == 200
        assert device.json()["device_id"] == "test-pollipi"
        assert "secret" not in device.text.lower()

        status = client.get("/status")
        assert status.status_code == 200
        assert status.json()["running"] is False
        assert status.json()["mesh_shadow_mode"] is True

        started = client.post("/start", json={"interval_sec": 1, "mesh_shadow_mode": True})
        assert started.status_code == 200
        assert started.json()["running"] is True

        deadline = time.monotonic() + 5
        images_payload = {"images": []}
        while time.monotonic() < deadline:
            images = client.get("/images")
            assert images.status_code == 200
            images_payload = images.json()
            if images_payload["images"]:
                break
            time.sleep(0.2)

        assert images_payload["image_count"] >= 1
        filename = images_payload["images"][0]["filename"]
        assert client.get(f"/images/{filename}").status_code == 200
        assert client.get("/latest").status_code == 200

        current = client.get("/status").json()
        assert current["mesh_shadow_mode"] is True
        assert current["motion_trigger_mode"] is False
        assert current["hybrid_mode"] is False
        assert current["ml_assist_mode"] is False
        assert current["roi_used"] is False

        stopped = client.post("/stop")
        assert stopped.status_code == 200
        assert stopped.json()["running"] is False


def test_device_secret_protects_active_endpoints(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path, device_secret="field-secret") as client:
        assert client.get("/device").status_code == 200
        assert client.get("/status").status_code == 200

        protected_requests = [
            ("post", "/start", {"json": {"interval_sec": 1}}),
            ("post", "/stop", {}),
            ("get", "/images", {}),
            ("get", "/mjpeg", {}),
        ]
        for method, path, kwargs in protected_requests:
            response = getattr(client, method)(path, **kwargs)
            assert response.status_code == 401, path

        headers = {SECRET_HEADER: "field-secret"}
        started = client.post("/start", json={"interval_sec": 1}, headers=headers)
        assert started.status_code == 200
        assert client.get("/images", headers=headers).status_code == 200
        assert client.post("/stop", headers=headers).status_code == 200


def test_active_api_excludes_retired_candidate_training_and_roi_routes(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        assert client.get("/status").status_code == 200
        assert client.get("/events").status_code == 404
        assert client.get("/training/status").status_code == 404
        assert client.get("/roi/suggest").status_code == 404
        assert client.get("/compat/events").status_code == 404
        assert client.get("/compat/training/status").status_code == 404
        rejected = client.post(
            "/start",
            json={"interval_sec": 1, "roi_x": 0, "roi_y": 0, "roi_w": 10, "roi_h": 10},
        )
        assert rejected.status_code == 410
