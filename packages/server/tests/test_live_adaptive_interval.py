"""Actual adaptive interval (live) is gated behind three conditions and applies
the three-stage interval to real high-res scheduling, recomputed every probe."""
from __future__ import annotations

import csv
import importlib
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError


def _clear() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _import_capture_loop(monkeypatch, *, live_env: bool):
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    if live_env:
        monkeypatch.setenv("POLLIPI_LIVE_ADAPTIVE_ENABLED", "1")
    else:
        monkeypatch.delenv("POLLIPI_LIVE_ADAPTIVE_ENABLED", raising=False)
    _clear()
    return importlib.import_module("visit_monitor_server.services.capture_loop")


def _client(monkeypatch, tmp_path, *, live_env: bool):
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    monkeypatch.setenv("POLLIPI_PROBE_INTERVAL_SEC", "0.02")
    monkeypatch.delenv("POLLIPI_DEVICE_SECRET", raising=False)
    if live_env:
        monkeypatch.setenv("POLLIPI_LIVE_ADAPTIVE_ENABLED", "1")
    else:
        monkeypatch.delenv("POLLIPI_LIVE_ADAPTIVE_ENABLED", raising=False)
    _clear()
    return importlib.import_module("visit_monitor_server.app").create_app()


def test_live_requires_all_three_gates(monkeypatch) -> None:
    cap = _import_capture_loop(monkeypatch, live_env=True)
    from pollipi_analysis.policy import get_policy_profile

    canary = get_policy_profile("three_stage_canary_v1")
    default = get_policy_profile("three_stage_default_v1")
    req_yes = SimpleNamespace(live_adaptive_requested=True)
    req_no = SimpleNamespace(live_adaptive_requested=False)

    # All three true -> active.
    assert cap.live_adaptive_active(req_yes, canary) is True
    # Any one false -> inactive.
    assert cap.live_adaptive_active(req_no, canary) is False  # request off
    assert cap.live_adaptive_active(req_yes, default) is False  # profile.live_allowed false


def test_live_inactive_when_env_off(monkeypatch) -> None:
    cap = _import_capture_loop(monkeypatch, live_env=False)
    from pollipi_analysis.policy import get_policy_profile

    canary = get_policy_profile("three_stage_canary_v1")
    req_yes = SimpleNamespace(live_adaptive_requested=True)
    assert cap.live_adaptive_active(req_yes, canary) is False  # env gate off


def test_compute_next_due_recomputes_from_last_save(monkeypatch) -> None:
    cap = _import_capture_loop(monkeypatch, live_env=True)
    # First frame (no prior save) is due immediately.
    assert cap.compute_next_due(None, 30.0, 1000.0) == 1000.0
    # Next due is last_save + the *current* desired interval.
    assert cap.compute_next_due(1000.0, 30.0, 1005.0) == 1030.0
    # If the desired interval shrank to 5 s and >=5 s already elapsed, it's due now.
    assert cap.compute_next_due(1000.0, 5.0, 1007.0) == 1005.0  # <= now -> fires


def test_canary_profile_allows_live_default_does_not(monkeypatch) -> None:
    _import_capture_loop(monkeypatch, live_env=False)
    from pollipi_analysis.policy import get_policy_profile

    assert get_policy_profile("three_stage_canary_v1").live_allowed is True
    assert get_policy_profile("three_stage_default_v1").live_allowed is False


def _probe_log(images_dir: Path):
    files = sorted(images_dir.glob("adaptive_probe_shadow_v2_*.csv"))
    return files[0] if files else None


def test_default_run_is_shadow_only_fixed_interval(monkeypatch, tmp_path) -> None:
    app = _client(monkeypatch, tmp_path, live_env=False)
    images_dir = tmp_path / "images"
    with TestClient(app) as client:
        assert client.post("/start", json={"interval_sec": 1}).status_code == 200
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            log = _probe_log(images_dir)
            if log is not None and sum(1 for _ in log.open(encoding="utf-8")) >= 6:
                break
            time.sleep(0.1)
        status = client.get("/status").json()
        client.post("/stop")

    assert status["live_adaptive_active"] is False
    rows = list(csv.DictReader(_probe_log(images_dir).open(encoding="utf-8")))
    assert rows and all(r["live_adaptive_active"] == "False" for r in rows)
    assert all(r["applied_interval_sec"] == "1.000" for r in rows)  # fixed, not adaptive


def test_fast_interval_must_be_below_normal(monkeypatch) -> None:
    _clear()
    from visit_monitor_server.api.schemas.capture import StartRequest

    # fast >= normal is rejected.
    with pytest.raises(ValidationError):
        StartRequest(interval_sec=10, fast_interval_sec=10)
    with pytest.raises(ValidationError):
        StartRequest(interval_sec=10, fast_interval_sec=20)
    # fast < normal is accepted; omitting it is accepted (profile default used).
    assert StartRequest(interval_sec=30, fast_interval_sec=10).fast_interval_sec == 10
    assert StartRequest(interval_sec=30).fast_interval_sec is None


def test_fast_interval_overrides_mid_in_live_run(monkeypatch, tmp_path) -> None:
    """In a live run, LOW = interval_sec and MID = fast_interval_sec (overriding profile)."""
    app = _client(monkeypatch, tmp_path, live_env=True)
    images_dir = tmp_path / "images"
    with TestClient(app) as client:
        # Use the no-classification motion profile so any fake-scene motion shows MID.
        started = client.post(
            "/start",
            json={
                "interval_sec": 30,
                "fast_interval_sec": 7,
                "policy_profile_id": "three_stage_motion_canary_v1",
                "live_adaptive_requested": True,
            },
        )
        assert started.status_code == 200
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            log = _probe_log(images_dir)
            if log is not None and sum(1 for _ in log.open(encoding="utf-8")) >= 6:
                break
            time.sleep(0.1)
        client.post("/stop")

    rows = list(csv.DictReader(_probe_log(images_dir).open(encoding="utf-8")))
    applied = {r["applied_interval_sec"] for r in rows}
    # Only the user-set LOW (30) and fast MID (7) may appear — never the profile's 10.
    assert applied <= {"30.000", "7.000"}
    assert "10.000" not in applied


def test_canary_live_applies_adaptive_interval(monkeypatch, tmp_path) -> None:
    app = _client(monkeypatch, tmp_path, live_env=True)
    images_dir = tmp_path / "images"
    with TestClient(app) as client:
        started = client.post(
            "/start",
            json={
                "interval_sec": 30,
                "policy_profile_id": "three_stage_canary_v1",
                "live_adaptive_requested": True,
            },
        )
        assert started.status_code == 200
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            log = _probe_log(images_dir)
            if log is not None and sum(1 for _ in log.open(encoding="utf-8")) >= 6:
                break
            time.sleep(0.1)
        status = client.get("/status").json()
        client.post("/stop")

    # Live gate satisfied; a quiet fake scene stays LOW, and LOW is the user's normal
    # interval (interval_sec=30), which live mode applies to the schedule.
    assert status["live_adaptive_active"] is True
    assert status["live_allowed"] is True
    rows = list(csv.DictReader(_probe_log(images_dir).open(encoding="utf-8")))
    assert rows and all(r["live_adaptive_active"] == "True" for r in rows)
    assert rows[0]["schema_version"] == "probe-shadow-2"
    assert "run_id" in rows[0] and rows[0]["run_id"]
    assert all(r["applied_interval_sec"] == "30.000" for r in rows)
