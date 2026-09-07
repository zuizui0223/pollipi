from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def test_fake_camera_probability_audit_window_smoke(monkeypatch, tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(image_dir))
    monkeypatch.setenv("POLLIPI_DEVICE_ID", "audit-pi")
    monkeypatch.setenv("POLLIPI_DEVICE_NAME", "Audit Test Pi")
    monkeypatch.setenv("POLLIPI_PROBE_INTERVAL_SEC", "0.1")
    monkeypatch.delenv("POLLIPI_LIVE_ADAPTIVE_ENABLED", raising=False)
    monkeypatch.setenv("POLLIPI_AUDIT_ENABLED", "true")
    monkeypatch.setenv("POLLIPI_AUDIT_SEED", "audit-smoke-seed")
    monkeypatch.setenv("POLLIPI_AUDIT_Q_SELECTED", "1")
    monkeypatch.setenv("POLLIPI_AUDIT_Q_OMITTED", "1")
    monkeypatch.setenv("POLLIPI_AUDIT_WINDOW_PROBES", "3")
    monkeypatch.setenv("POLLIPI_AUDIT_REFERENCE_ROI", "0,0,0.5,1")

    _clear_server_modules()
    app_module = importlib.import_module("visit_monitor_server.app")

    with TestClient(app_module.create_app()) as client:
        started = client.post(
            "/start",
            json={"interval_sec": 1, "mesh_shadow_mode": True},
        )
        assert started.status_code == 200

        deadline = time.monotonic() + 8.0
        window_dirs: list[Path] = []
        while time.monotonic() < deadline:
            audit_roots = list((image_dir / "probability_audit").glob("*/windows/*"))
            window_dirs = [path for path in audit_roots if path.is_dir()]
            if window_dirs:
                break
            time.sleep(0.1)

        assert window_dirs, "audit window was not materialized by fake-camera run"
        stopped = client.post("/stop")
        assert stopped.status_code == 200

    run_roots = [path for path in (image_dir / "probability_audit").iterdir() if path.is_dir()]
    assert len(run_roots) == 1
    root = run_roots[0]
    assert (root / "audit_draws.csv").is_file()
    assert (root / "config.json").is_file()
    assert (root / "run_summary.json").is_file()

    summary = json.loads((root / "run_summary.json").read_text())
    assert summary["draw_count"] >= 3
    assert summary["completed_window_count"] >= 1
    # q=1 makes run-edge audit centres explicit rather than silently deleting them.
    assert len(summary["incomplete_included_centres"]) >= 1

    first_window = sorted((root / "windows").iterdir())[0]
    manifest = json.loads((first_window / "manifest.json").read_text())
    assert manifest["window_size"] == 3
    assert len(manifest["samples"]) == 3
    primary = np.load(first_window / manifest["samples"][0]["primary_file"])
    reference = np.load(first_window / manifest["samples"][0]["reference_file"])
    assert primary.ndim == 2
    assert reference.ndim == 2
    assert primary.shape[0] == reference.shape[0]
    assert 0 < reference.shape[1] < primary.shape[1]
