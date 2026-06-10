from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    monkeypatch.setenv("POLLIPI_DEVICE_ID", "test-pollipi")
    monkeypatch.setenv("POLLIPI_DEVICE_NAME", "Test PolliPi")
    _clear_server_modules()
    app_module = importlib.import_module("visit_monitor_server.app")
    return TestClient(app_module.create_app())


def test_fake_camera_exchange_smoke(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        device = client.get("/device")
        assert device.status_code == 200
        assert device.json()["device_id"] == "test-pollipi"

        status = client.get("/status")
        assert status.status_code == 200
        assert status.json()["running"] is False

        started = client.post("/start", json={"interval_sec": 1, "auto_mode": False})
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

        training = client.get("/training/status")
        assert training.status_code == 200
        assert "model_available" in training.json()

        stopped = client.post("/stop")
        assert stopped.status_code == 200
        assert stopped.json()["running"] is False

