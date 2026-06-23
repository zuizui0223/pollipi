from __future__ import annotations

import csv
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


def _client(monkeypatch, tmp_path: Path, *, device_secret: str | None = None, legacy_routes: bool = False) -> TestClient:
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    monkeypatch.setenv("POLLIPI_DEVICE_ID", "test-pollipi")
    monkeypatch.setenv("POLLIPI_DEVICE_NAME", "Test PolliPi")
    monkeypatch.delenv("POLLIPI_GIT_COMMIT", raising=False)
    monkeypatch.delenv("POLLIPI_BUILD_TIMESTAMP", raising=False)
    monkeypatch.delenv("POLLIPI_DEPLOYMENT_MODE", raising=False)
    monkeypatch.delenv("POLLIPI_WEB_BUILD_ID", raising=False)
    if device_secret is None:
        monkeypatch.delenv("POLLIPI_DEVICE_SECRET", raising=False)
    else:
        monkeypatch.setenv("POLLIPI_DEVICE_SECRET", device_secret)
    if legacy_routes:
        monkeypatch.setenv("POLLIPI_ENABLE_LEGACY_ROUTES", "1")
    else:
        monkeypatch.delenv("POLLIPI_ENABLE_LEGACY_ROUTES", raising=False)
    _clear_server_modules()
    app_module = importlib.import_module("visit_monitor_server.app")
    return TestClient(app_module.create_app())


def test_fake_camera_exchange_smoke(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path, legacy_routes=True) as client:
        device = client.get("/device")
        assert device.status_code == 200
        assert device.json()["device_id"] == "test-pollipi"
        assert device.json()["build_info"]["deployment_mode"] == "unknown"
        assert "secret" not in device.text.lower()

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

        # Bulk delete images test
        bulk_del_img = client.post("/images/bulk-delete", json={"filenames": [filename]})
        assert bulk_del_img.status_code == 200
        assert bulk_del_img.json()["deleted_count"] == 1

        event_log = tmp_path / "images" / "event_log.csv"
        with event_log.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "timestamp",
                    "image_filename",
                    "motion_score",
                    "changed_area_ratio",
                    "small_blob_count",
                    "insect_candidate",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "timestamp": "2026-06-10T12:00:00+09:00",
                "image_filename": "missing.jpg",
                "motion_score": "0.02",
                "changed_area_ratio": "0.02",
                "small_blob_count": "1",
                "insect_candidate": "true",
            })

        events = client.get("/compat/events")
        assert events.status_code == 200
        event_payload = events.json()
        assert event_payload["event_count"] == 1
        event_id = event_payload["events"][0]["event_id"]
        assert event_id.startswith("fallback-")
        assert event_payload["events"][0]["review_status"] == "motion_candidate"

        bulk_del_ev = client.post("/compat/events/bulk-delete", json={"event_ids": [event_id], "scope": "event_only"})
        assert bulk_del_ev.status_code == 200
        assert bulk_del_ev.json()["deleted_count"] == 1
        assert client.get("/compat/events").json()["event_count"] == 0

        baseline_image = tmp_path / "images" / "baseline.jpg"
        baseline_image.write_bytes(b"baseline")
        observation_log = tmp_path / "images" / "observation_events.csv"
        with observation_log.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "capture_type", "image_filename"])
            writer.writeheader()
            writer.writerow({
                "timestamp": "2026-06-10T12:00:01+09:00",
                "capture_type": "scheduled",
                "image_filename": baseline_image.name,
            })
        with event_log.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["event_id", "timestamp", "image_filename"])
            writer.writeheader()
            writer.writerow({
                "event_id": "event_unsafe_baseline",
                "timestamp": "2026-06-10T12:00:02+09:00",
                "image_filename": baseline_image.name,
            })
        unsafe_delete = client.post(
            "/compat/events/bulk-delete",
            json={"event_ids": ["event_unsafe_baseline"], "scope": "event_and_event_image"},
        )
        assert unsafe_delete.status_code == 200
        unsafe_payload = unsafe_delete.json()
        assert unsafe_payload["deleted_count"] == 1
        assert unsafe_payload["image_deleted_count"] == 0
        assert unsafe_payload["failed"][0]["event_id"] == "event_unsafe_baseline"
        assert baseline_image.is_file()
        assert client.get("/compat/events").json()["event_count"] == 0

        event_image = tmp_path / "images" / "event_only.jpg"
        unknown_image = tmp_path / "images" / "unknown.jpg"
        scheduled_event_image = tmp_path / "images" / "scheduled_event.jpg"
        event_image.write_bytes(b"event")
        unknown_image.write_bytes(b"unknown")
        scheduled_event_image.write_bytes(b"scheduled-event")
        with observation_log.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "capture_type", "image_filename"])
            writer.writeheader()
            writer.writerow({
                "timestamp": "2026-06-10T12:01:00+09:00",
                "capture_type": "event",
                "image_filename": event_image.name,
            })
            writer.writerow({
                "timestamp": "2026-06-10T12:01:01+09:00",
                "capture_type": "scheduled_event",
                "image_filename": scheduled_event_image.name,
            })
        with event_log.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["event_id", "timestamp", "image_filename"])
            writer.writeheader()
            writer.writerows([
                {
                    "event_id": "event_only",
                    "timestamp": "2026-06-10T12:01:00+09:00",
                    "image_filename": event_image.name,
                },
                {
                    "event_id": "unknown_provenance",
                    "timestamp": "2026-06-10T12:01:01+09:00",
                    "image_filename": unknown_image.name,
                },
                {
                    "event_id": "scheduled_event",
                    "timestamp": "2026-06-10T12:01:02+09:00",
                    "image_filename": scheduled_event_image.name,
                },
                {
                    "event_id": "missing_filename",
                    "timestamp": "2026-06-10T12:01:03+09:00",
                    "image_filename": "",
                },
            ])
        selective_delete = client.post(
            "/compat/events/bulk-delete",
            json={
                "event_ids": ["event_only", "unknown_provenance", "scheduled_event", "missing_filename"],
                "scope": "event_and_event_image",
            },
        )
        assert selective_delete.status_code == 200
        selective_payload = selective_delete.json()
        assert selective_payload["deleted_count"] == 4
        assert selective_payload["image_deleted_count"] == 1
        failure_reasons = {item["event_id"]: item["reason"] for item in selective_payload["failed"]}
        assert "unknown" in failure_reasons["unknown_provenance"]
        assert "scheduled/baseline" in failure_reasons["scheduled_event"]
        assert "no image filename" in failure_reasons["missing_filename"]
        assert not event_image.exists()
        assert unknown_image.is_file()
        assert scheduled_event_image.is_file()
        assert client.get("/compat/events").json()["event_count"] == 0

        training = client.get("/compat/training/status")
        assert training.status_code == 200
        assert "model_available" in training.json()

        stopped = client.post("/stop")
        assert stopped.status_code == 200
        assert stopped.json()["running"] is False


def test_device_secret_protects_configured_endpoints(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path, device_secret="field-secret", legacy_routes=True) as client:
        assert client.get("/device").status_code == 200
        assert client.get("/status").status_code == 200
        assert client.get("/preview").status_code == 200

        protected_requests = [
            ("post", "/start", {"json": {"interval_sec": 1}}),
            ("post", "/stop", {}),
            ("get", "/images", {}),
            ("get", "/compat/events", {}),
            ("get", "/exports/images.zip", {}),
            ("get", "/compat/training/status", {}),
            ("get", "/mjpeg", {}),
        ]
        for method, path, kwargs in protected_requests:
            response = getattr(client, method)(path, **kwargs)
            assert response.status_code == 401, path

        headers = {SECRET_HEADER: "field-secret"}
        started = client.post("/start", json={"interval_sec": 1}, headers=headers)
        assert started.status_code == 200
        assert client.get("/images", headers=headers).status_code == 200
        assert client.get("/compat/events", headers=headers).status_code == 200
        assert client.get("/compat/training/status", headers=headers).status_code == 200
        assert client.post("/stop", headers=headers).status_code == 200


def test_active_default_excludes_legacy_candidate_training_and_roi(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        assert client.get("/status").status_code == 200
        assert client.get("/events").status_code == 404
        assert client.get("/training/status").status_code == 404
        assert client.get("/roi/suggest").status_code == 404
        assert client.get("/compat/events").status_code == 404
        rejected = client.post("/start", json={"interval_sec": 1, "roi_x": 0, "roi_y": 0, "roi_w": 10, "roi_h": 10})
        assert rejected.status_code == 410
