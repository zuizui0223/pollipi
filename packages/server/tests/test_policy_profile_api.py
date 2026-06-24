"""Selectable policy profile wiring for shadow-only capture."""
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


def test_unknown_policy_profile_is_rejected(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/start",
            json={"interval_sec": 30, "policy_profile_id": "not-approved"},
        )

    assert response.status_code == 422
    assert "unknown policy_profile_id" in response.text


def test_policy_profile_is_fixed_while_capture_runs(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        started = client.post(
            "/start",
            json={"interval_sec": 30, "policy_profile_id": "three_stage_default_v1"},
        )
        changed = client.post(
            "/start",
            json={"interval_sec": 30, "policy_profile_id": "three_stage_sensitive_v1"},
        )
        status = client.get("/status").json()
        client.post("/stop")

    assert started.status_code == 200
    assert changed.status_code == 409
    assert status["policy_profile_id"] == "three_stage_default_v1"
    assert status["simulation_run_id"] == "issue27-three-stage-baseline"
    assert status["kind"] == "three_stage"
    assert status["live_adaptive_enabled"] is False


def test_probe_csv_logs_policy_profile_provenance(monkeypatch, tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    probe_log = images_dir / "adaptive_probe_shadow-1.csv"

    with _client(monkeypatch, tmp_path) as client:
        assert client.post(
            "/start",
            json={"interval_sec": 1, "policy_profile_id": "three_stage_sensitive_v1"},
        ).status_code == 200

        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            if probe_log.exists() and sum(1 for _ in probe_log.open(encoding="utf-8")) >= 4:
                break
            time.sleep(0.1)

        status = client.get("/status").json()
        client.post("/stop")

    assert status["policy_profile_id"] == "three_stage_sensitive_v1"
    assert status["simulation_run_id"] == "issue27-three-stage-sensitive"
    assert status["kind"] == "three_stage"
    rows = list(csv.DictReader(probe_log.open(encoding="utf-8")))
    assert rows
    assert {row["policy_profile_id"] for row in rows} == {"three_stage_sensitive_v1"}
    assert {row["simulation_run_id"] for row in rows} == {"issue27-three-stage-sensitive"}
    assert {row["kind"] for row in rows} == {"three_stage"}
