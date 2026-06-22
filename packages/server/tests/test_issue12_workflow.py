from __future__ import annotations

import csv
import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    _clear_server_modules()
    app_module = importlib.import_module("visit_monitor_server.app")
    return TestClient(app_module.create_app())


def test_candidate_review_uses_visit_noise_unclear_and_training_counts(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        image_dir = tmp_path / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        event_log = image_dir / "event_log.csv"
        with event_log.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["event_id", "timestamp", "image_filename"])
            writer.writeheader()
            writer.writerow({"event_id": "e1", "timestamp": "2026-06-22T12:00:00+09:00", "image_filename": "e1.jpg"})
            writer.writerow({"event_id": "e2", "timestamp": "2026-06-22T12:00:01+09:00", "image_filename": "e2.jpg"})
            writer.writerow({"event_id": "e3", "timestamp": "2026-06-22T12:00:02+09:00", "image_filename": "e3.jpg"})

        assert client.post("/events/e1/label", json={"manual_label": "visit"}).status_code == 200
        assert client.post("/events/e2/label", json={"manual_label": "noise", "false_positive_reason": "wind"}).status_code == 200
        assert client.post("/events/e3/label", json={"manual_label": "unclear"}).status_code == 200

        events = {row["event_id"]: row for row in client.get("/events", params={"category": "all"}).json()["events"]}
        assert events["e1"]["review_label"] == "visit"
        assert events["e1"]["final_category"] == "positive"
        assert events["e2"]["review_label"] == "noise"
        assert events["e2"]["final_category"] == "negative"
        assert events["e3"]["review_label"] == "unclear"
        assert events["e3"]["final_category"] == "unclear"

        training = client.get("/training/status").json()
        assert training["positive_count"] == 1
        assert training["negative_count"] == 1
        assert training["reviewed_count"] == 2


def test_motion_features_include_floral_display_control_and_grid() -> None:
    import numpy as np

    from visit_monitor_server.services.motion import detect_motion

    background = np.zeros((10, 10), dtype=np.float32)
    frame = np.zeros((30, 20), dtype=np.float32)
    frame[:20, :20] = 0
    frame[2:4, 2:4] = 255

    metrics, detected, _ = detect_motion(
        frame,
        background,
        pixel_difference=20,
        motion_ratio=0.001,
        roi=(0, 0, 10, 10),
        control_roi=(10, 10, 5, 5),
        grid_shape=(4, 4),
        monitor_size=(20, 20),
    )

    assert detected is True
    assert metrics["roi_semantics"] == "floral_display_zone"
    assert metrics["control_roi_used"] is True
    assert metrics["floral_zone_score"] > metrics["background_control_score"]
    assert metrics["changed_cell_count"] > 0
    assert "localized_change" in metrics["candidate_reasons"]
