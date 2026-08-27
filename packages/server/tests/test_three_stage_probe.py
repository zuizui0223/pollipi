"""Issue #27 server wiring: probe-only three-stage shadow loop.

Low-res probes run far more often than high-res saves, the high-res cadence
stays fixed, and status reports a would-be mode with live adaptive control OFF.
TNOA Phase A adds a parallel fail-closed evidence row per probe without changing
that existing timing contract.
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


def _probe_log(images_dir: Path):
    files = sorted(images_dir.glob("adaptive_probe_shadow_v2_*.csv"))
    return files[0] if files else None


def _tnoa_log(images_dir: Path):
    files = sorted(images_dir.glob("tnoa_observation_v1_*.csv"))
    return files[0] if files else None


def test_probes_outnumber_highres_saves_and_status_reports_would_be_mode(monkeypatch, tmp_path: Path) -> None:
    images_dir = tmp_path / "images"

    with _client(monkeypatch, tmp_path) as client:
        # High-res every 1 s; probes every 0.02 s.
        assert client.post("/start", json={"interval_sec": 1}).status_code == 200

        # The loop has a ~2 s startup wait; poll past it until probes accumulate.
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            log = _probe_log(images_dir)
            tnoa = _tnoa_log(images_dir)
            if (
                log is not None
                and tnoa is not None
                and sum(1 for _ in log.open(encoding="utf-8")) >= 6
                and sum(1 for _ in tnoa.open(encoding="utf-8")) >= 6
            ):
                break
            time.sleep(0.1)

        status = client.get("/status").json()
        client.post("/stop")

    # Shadow-only honesty: would-be mode present, live adaptive OFF, shadow ON.
    assert status["would_be_mode"] in {"LOW", "MID", "HIGH"}
    assert status["live_adaptive_enabled"] is False
    assert status["live_adaptive_active"] is False
    assert status["mesh_shadow_mode"] is True
    assert status["probe_interval_sec"] == 0.02
    assert status["interval_sec"] == 1

    # Existing probe-shadow contract remains unchanged.
    probe_log = _probe_log(images_dir)
    assert probe_log is not None
    rows = list(csv.DictReader(probe_log.open(encoding="utf-8")))
    assert len(rows) >= 5
    highres_saves = sum(1 for r in rows if r["actual_highres_saved"] == "True")
    saved_images = len(list(images_dir.glob("image_*.jpg")))
    assert highres_saves == saved_images
    assert len(rows) > highres_saves
    assert all(r["validation_status"] == "synthetic_only" for r in rows)
    assert all(r["policy_profile_id"] == "three_stage_default_v1" for r in rows)
    assert all(r["simulation_run_id"] == "issue27-three-stage-baseline" for r in rows)
    assert all(r["kind"] == "three_stage" for r in rows)
    assert all(r["live_allowed"] == "False" for r in rows)

    # TNOA adds one parallel row per completed probe and stays fail-closed.
    tnoa_log = _tnoa_log(images_dir)
    assert tnoa_log is not None
    tnoa_rows = list(csv.DictReader(tnoa_log.open(encoding="utf-8")))
    assert len(tnoa_rows) == len(rows)
    assert all(r["schema_version"] == "tnoa-shadow-1" for r in tnoa_rows)
    assert all(r["calibration_status"] == "unavailable" for r in tnoa_rows)
    assert all(r["observation_state"] == "U" for r in tnoa_rows)
    assert all(r["would_be_action"] == "observe_only" for r in tnoa_rows)
    assert all(r["action_applied"] == "False" for r in tnoa_rows)
    assert all(r["target_calibrated_support"] == "" for r in tnoa_rows)
    assert all(r["nuisance_calibrated_support"] == "" for r in tnoa_rows)
    assert all(r["observability_calibrated_support"] == "" for r in tnoa_rows)
    assert all(r["absence_available"] == "False" for r in tnoa_rows)
