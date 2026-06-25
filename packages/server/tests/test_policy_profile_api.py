"""Selectable policy profile wiring for shadow-only capture."""
from __future__ import annotations

import csv
import importlib
import json
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


def _profile_payload(profile_id: str, simulation_run_id: str | None = None) -> dict:
    return {
        "schema": "pollipi-policy-profile-1",
        "profile_id": profile_id,
        "simulation_run_id": simulation_run_id or f"run-{profile_id}",
        "source_commit": f"analysis-{profile_id}",
        "kind": "three_stage",
        "live_allowed": False,
        "description": "test profile",
        "parameters": {
            "low_interval_sec": 30.0,
            "mid_interval_sec": 15.0,
            "high_interval_sec": 5.0,
            "high_hard_cap_sec": 120.0,
            "high_exit_quiet_probes": 3,
        },
    }


def _write_profile(directory: Path, name: str, payload: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")


def test_policy_profiles_endpoint_reads_json_registry(monkeypatch, tmp_path: Path) -> None:
    profile_dir = tmp_path / "profiles"
    _write_profile(profile_dir, "default.json", _profile_payload("three_stage_default_v1"))
    _write_profile(profile_dir, "extra.json", _profile_payload("three_stage_extra_v1"))
    monkeypatch.setenv("POLLIPI_POLICY_PROFILE_DIR", str(profile_dir))

    with _client(monkeypatch, tmp_path) as client:
        response = client.get("/policy-profiles")

    assert response.status_code == 200
    body = response.json()
    assert body["default_profile_id"] == "three_stage_default_v1"
    profiles = {profile["profile_id"]: profile for profile in body["profiles"]}
    assert "three_stage_extra_v1" in profiles
    assert profiles["three_stage_extra_v1"]["live_allowed"] is False


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
    assert status["live_allowed"] is False
    assert status["live_adaptive_enabled"] is False


def test_probe_csv_logs_policy_profile_provenance(monkeypatch, tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    probe_log = None

    with _client(monkeypatch, tmp_path) as client:
        assert client.post(
            "/start",
            json={"interval_sec": 1, "policy_profile_id": "three_stage_sensitive_v1"},
        ).status_code == 200

        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            probe_logs = sorted(images_dir.glob("adaptive_probe_shadow_v2_*.csv"))
            if len(probe_logs) == 1:
                candidate = probe_logs[0]
                if sum(1 for _ in candidate.open(encoding="utf-8")) >= 4:
                    probe_log = candidate
                    break
            time.sleep(0.1)

        assert probe_log is not None, (
            "Expected one v2 probe log with at least three records."
        )
        status = client.get("/status").json()
        client.post("/stop")

    assert status["policy_profile_id"] == "three_stage_sensitive_v1"
    assert status["simulation_run_id"] == "issue27-three-stage-sensitive"
    assert status["kind"] == "three_stage"
    assert status["live_allowed"] is False
    rows = list(csv.DictReader(probe_log.open(encoding="utf-8")))
    assert rows
    assert {row["policy_profile_id"] for row in rows} == {"three_stage_sensitive_v1"}
    assert {row["simulation_run_id"] for row in rows} == {"issue27-three-stage-sensitive"}
    assert {row["kind"] for row in rows} == {"three_stage"}
    assert {row["live_allowed"] for row in rows} == {"False"}


def test_pwa_uses_policy_profiles_api_instead_of_hardcoded_profiles() -> None:
    root = Path(__file__).resolve().parents[3]
    session_source = (root / "packages" / "web" / "src" / "state" / "session.ts").read_text(encoding="utf-8")
    app_source = (root / "packages" / "web" / "src" / "app.tsx").read_text(encoding="utf-8")
    client_source = (root / "packages" / "web" / "src" / "api" / "client.ts").read_text(encoding="utf-8")

    assert "fetchPolicyProfiles" in client_source
    assert "fetchPolicyProfiles" in app_source
    assert "three_stage_sensitive_v1" not in session_source
