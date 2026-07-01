"""Storage-location switch: redirect captures to a different directory (e.g. USB).

These tests simulate an external mount with an arbitrary tmp directory (the same
code path that runs on the Pi when the target is /media/<user>/<LABEL>/images)
and prove that a switch redirects new photos and adaptive logs, is rejected
while capture is running, and can be reset back to the SD-card default.
"""
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


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "sd" / "images"))
    monkeypatch.setenv("POLLIPI_DEVICE_ID", "test-pollipi")
    monkeypatch.delenv("POLLIPI_DEVICE_SECRET", raising=False)
    _clear_server_modules()
    app_module = importlib.import_module("visit_monitor_server.app")
    return TestClient(app_module.create_app())


def _wait_for_first_image(client: TestClient) -> dict:
    deadline = time.monotonic() + 6
    payload = {"images": [], "image_count": 0}
    while time.monotonic() < deadline:
        payload = client.get("/images").json()
        if payload["images"]:
            return payload
        time.sleep(0.2)
    return payload


def test_storage_reports_default_target(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        info = client.get("/storage").json()
        assert info["current_path"] == str(tmp_path / "sd" / "images")
        assert info["default_path"] == str(tmp_path / "sd" / "images")
        assert info["capture_running"] is False
        # The SD default is always offered and flagged.
        default_target = next(t for t in info["targets"] if t["is_default"])
        assert default_target["is_current"] is True


def test_switch_redirects_new_captures(monkeypatch, tmp_path: Path) -> None:
    usb_images = tmp_path / "usb" / "images"
    with _client(monkeypatch, tmp_path) as client:
        switched = client.post("/storage", json={"path": str(usb_images)})
        assert switched.status_code == 200
        body = switched.json()
        assert body["current_path"] == str(usb_images)
        assert usb_images.is_dir()  # created and write-tested by the endpoint

        started = client.post("/start", json={"interval_sec": 1, "mesh_shadow_mode": True})
        assert started.status_code == 200

        payload = _wait_for_first_image(client)
        assert payload["image_count"] >= 1
        assert payload["image_dir"] == str(usb_images)

        # The adaptive metrics log is written from the second capture onward (the
        # first frame has no reference to diff against). Wait for it to confirm the
        # logs follow the photos to external storage.
        metrics_csv = usb_images / "adaptive_metrics.csv"
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline and not metrics_csv.exists():
            time.sleep(0.2)

        client.post("/stop")

        # Photos and the adaptive metrics log landed on the "USB", not the SD card.
        jpegs = list(usb_images.glob("*.jpg"))
        assert jpegs, "expected at least one JPEG on the external target"
        assert metrics_csv.exists()
        sd_images = tmp_path / "sd" / "images"
        assert not list(sd_images.glob("*.jpg"))


def test_switch_rejected_while_running(monkeypatch, tmp_path: Path) -> None:
    usb_images = tmp_path / "usb" / "images"
    with _client(monkeypatch, tmp_path) as client:
        client.post("/start", json={"interval_sec": 1, "mesh_shadow_mode": True})
        try:
            blocked = client.post("/storage", json={"path": str(usb_images)})
            assert blocked.status_code == 409
        finally:
            client.post("/stop")


def test_reset_to_default_clears_override(monkeypatch, tmp_path: Path) -> None:
    usb_images = tmp_path / "usb" / "images"
    with _client(monkeypatch, tmp_path) as client:
        client.post("/storage", json={"path": str(usb_images)})
        reset = client.post("/storage", json={"path": None})
        assert reset.status_code == 200
        assert reset.json()["current_path"] == str(tmp_path / "sd" / "images")
        # The persisted override file is removed on reset.
        assert not (tmp_path / "sd" / "storage_config.json").exists()


def test_switch_requires_device_secret(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("POLLIPI_DEVICE_SECRET", "field-secret")
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "sd" / "images"))
    _clear_server_modules()
    app_module = importlib.import_module("visit_monitor_server.app")
    with TestClient(app_module.create_app()) as client:
        # GET is open; POST is protected.
        assert client.get("/storage").status_code == 200
        assert client.post("/storage", json={"path": None}).status_code == 401
        ok = client.post(
            "/storage",
            json={"path": None},
            headers={SECRET_HEADER: "field-secret"},
        )
        assert ok.status_code == 200
