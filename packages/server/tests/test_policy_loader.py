"""Issue #21 server wiring: the Pi loads a policy artifact and reports its
provenance in /status, without running any simulation/search."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _client(monkeypatch, tmp_path: Path, *, policy_path: Path | None = None) -> TestClient:
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    monkeypatch.delenv("POLLIPI_DEVICE_SECRET", raising=False)
    if policy_path is not None:
        monkeypatch.setenv("POLLIPI_POLICY_PATH", str(policy_path))
    else:
        monkeypatch.delenv("POLLIPI_POLICY_PATH", raising=False)
    _clear_server_modules()
    app_module = importlib.import_module("visit_monitor_server.app")
    return TestClient(app_module.create_app())


def test_status_defaults_to_baseline_policy_when_no_artifact(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        body = client.get("/status").json()
        assert body["policy_name"] == "baseline_rule"
        assert body["policy_version"] == "0"
        assert body["validation_status"] == "synthetic_only"


def test_status_reports_loaded_simulation_informed_policy(monkeypatch, tmp_path: Path) -> None:
    policy_path = tmp_path / "simulation_informed_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "schema": "policy-1",
                "policy_name": "simulation_informed",
                "policy_version": "1",
                "validation_status": "synthetic_only",
                "metadata": {"seed": 7},
                "feature": {"cell_size": 32, "pixel_difference": 20},
                "classifier": {"strong_spatial_concentration": 0.55},
            }
        ),
        encoding="utf-8",
    )
    with _client(monkeypatch, tmp_path, policy_path=policy_path) as client:
        body = client.get("/status").json()
        assert body["policy_name"] == "simulation_informed"
        assert body["policy_version"] == "1"
        assert body["validation_status"] == "synthetic_only"


def test_loader_falls_back_on_malformed_policy(monkeypatch, tmp_path: Path) -> None:
    policy_path = tmp_path / "simulation_informed_policy.json"
    policy_path.write_text("{ not valid json", encoding="utf-8")
    with _client(monkeypatch, tmp_path, policy_path=policy_path) as client:
        # A bad policy must not break the device; it falls back to baseline.
        body = client.get("/status").json()
        assert body["policy_name"] == "baseline_rule"
