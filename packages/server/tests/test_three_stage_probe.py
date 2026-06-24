"""Issue #27 server wiring: probe-only three-stage shadow loop.

Low-res probes run far more often than high-res saves, the high-res cadence
stays fixed, and status reports a would-be mode with live adaptive control OFF.
"""
from __future__ import annotations

import csv
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
    monkeypatch.setenv("POLLIPI_PROBE_INTERVAL_SEC", "0.02")
    monkeypatch.delenv("POLLIPI_DEVICE_SECRET", raising=False)
    monkeypatch.delenv("POLLIPI_LIVE_ADAPTIVE_ENABLED", raising=False)
    _clear_server_modules()
    app_module = importlib.import_module("visit_monitor_server.app")
    return TestClient(app_module.create_app())


def test_probes_outnumber_highres_saves_and_status_reports_would_be_mode(monkeypatch, tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    probe_log = images_dir / "adaptive_probe_shadow-1.csv"

    with _client(monkeypatch, tmp_path) as client:
        # High-res every 1 s; probes every 0.02 s.
        assert client.post("/start", json={"interval_sec": 1}).status_code == 200

        # The loop has a ~2 s startup wait; poll past it until probes accumulate.
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            if probe_log.exists() and sum(1 for _ in probe_log.open(encoding="utf-8")) >= 6:
                break
            time.sleep(0.1)

        status = client.get("/status").json()
        client.post("/stop")

    # Shadow-only honesty: would-be mode present, live adaptive OFF, shadow ON.
    assert status["would_be_mode"] in {"LOW", "MID", "HIGH"}
    assert status["live_adaptive_enabled"] is False
    assert status["mesh_shadow_mode"] is True
    assert status["probe_interval_sec"] == 0.02
    assert status["interval_sec"] == 1  # actual observed high-res gap stays fixed

    # The probe log has one row per probe; high-res saves stay sparse.
    rows = list(csv.DictReader(probe_log.open(encoding="utf-8")))
    assert len(rows) >= 5
    highres_saves = sum(1 for r in rows if r["actual_highres_saved"] == "True")
    saved_images = len(list(images_dir.glob("image_*.jpg")))
    assert highres_saves == saved_images
    # Far more probes than high-res saves within the run.
    assert len(rows) > highres_saves
    # Provenance present on every probe row.
    assert all(r["validation_status"] == "synthetic_only" for r in rows)
    assert all(r["policy_profile_id"] == "three_stage_default_v1" for r in rows)
    assert all(r["simulation_run_id"] == "issue27-three-stage-baseline" for r in rows)
    assert all(r["kind"] == "three_stage" for r in rows)
