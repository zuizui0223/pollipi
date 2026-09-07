from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from visit_monitor_server.services.audit_capture import (
    AuditCaptureConfig,
    AuditCaptureManager,
)


def _yuv420_frame(value: int, *, width: int = 8, height: int = 6) -> np.ndarray:
    # Picamera2 YUV420 arrays expose H*3/2 rows. Only the Y plane is scientifically
    # retained by the audit manager.
    frame = np.zeros((height * 3 // 2, width), dtype=np.uint8)
    frame[:height, :] = value
    return frame


def test_disabled_manager_has_no_side_effects(tmp_path: Path) -> None:
    manager = AuditCaptureManager(
        image_dir=tmp_path,
        run_id="run1",
        device_id="pi1",
        config=AuditCaptureConfig(enabled=False),
    )
    assert manager.enabled is False
    assert manager.root is None
    assert manager.add_probe(
        frame=_yuv420_frame(1), probe_timestamp="2026-09-07T10:00:00+09:00", selected=False
    ) is None
    manager.finalize()
    assert list(tmp_path.iterdir()) == []


def test_opportunity_id_matches_v3_adapter_rule() -> None:
    assert (
        AuditCaptureManager.opportunity_id(
            "pi1", "run1", "2026-09-07T10:00:05+09:00"
        )
        == "pi1|run1|2026-09-07T10:00:05+09:00"
    )


def test_enabled_manager_writes_complete_window_and_lossless_arrays(tmp_path: Path) -> None:
    manager = AuditCaptureManager(
        image_dir=tmp_path,
        run_id="run1",
        device_id="pi1",
        config=AuditCaptureConfig(
            enabled=True,
            seed="seed-v1",
            q_selected=1.0,
            q_omitted=1.0,
            window_size=3,
            reference_roi=(0.5, 0.0, 1.0, 1.0),
        ),
    )
    timestamps = [
        "2026-09-07T10:00:00+09:00",
        "2026-09-07T10:00:05+09:00",
        "2026-09-07T10:00:10+09:00",
    ]
    completed = None
    for index, timestamp in enumerate(timestamps):
        completed = manager.add_probe(
            frame=_yuv420_frame(index + 10),
            probe_timestamp=timestamp,
            selected=index == 1,
        )
    assert completed is not None
    assert completed.centre_opportunity_id.endswith(timestamps[1])
    manager.finalize()

    root = tmp_path / "probability_audit" / "run1"
    assert (root / "audit_draws.csv").is_file()
    summary = json.loads((root / "run_summary.json").read_text())
    assert summary["draw_count"] == 3
    assert summary["completed_window_count"] == 1
    assert summary["incomplete_included_centres"] == [
        f"pi1|run1|{timestamps[0]}",
        f"pi1|run1|{timestamps[2]}",
    ]

    window_dirs = list((root / "windows").iterdir())
    assert len(window_dirs) == 1
    manifest = json.loads((window_dirs[0] / "manifest.json").read_text())
    assert manifest["window_size"] == 3
    first_primary = np.load(window_dirs[0] / manifest["samples"][0]["primary_file"])
    first_reference = np.load(window_dirs[0] / manifest["samples"][0]["reference_file"])
    assert first_primary.shape == (6, 8)
    assert first_reference.shape == (6, 4)
    assert np.all(first_primary == 10)
    assert np.all(first_reference == 10)


def test_environment_is_fail_closed_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLLIPI_AUDIT_ENABLED", "true")
    monkeypatch.delenv("POLLIPI_AUDIT_SEED", raising=False)
    with pytest.raises(ValueError, match="POLLIPI_AUDIT_SEED"):
        AuditCaptureConfig.from_environment()


def test_environment_requires_positive_omitted_probability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POLLIPI_AUDIT_ENABLED", "true")
    monkeypatch.setenv("POLLIPI_AUDIT_SEED", "seed")
    monkeypatch.setenv("POLLIPI_AUDIT_Q_SELECTED", "0.2")
    monkeypatch.setenv("POLLIPI_AUDIT_Q_OMITTED", "0")
    monkeypatch.setenv("POLLIPI_AUDIT_REFERENCE_ROI", "0,0,0.25,1")
    with pytest.raises(ValueError, match="Q_OMITTED"):
        AuditCaptureConfig.from_environment()


def test_reference_roi_must_be_predeclared_and_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POLLIPI_AUDIT_ENABLED", "true")
    monkeypatch.setenv("POLLIPI_AUDIT_SEED", "seed")
    monkeypatch.setenv("POLLIPI_AUDIT_Q_SELECTED", "0.2")
    monkeypatch.setenv("POLLIPI_AUDIT_Q_OMITTED", "0.2")
    monkeypatch.setenv("POLLIPI_AUDIT_REFERENCE_ROI", "0.8,0,0.2,1")
    with pytest.raises(ValueError, match="REFERENCE_ROI"):
        AuditCaptureConfig.from_environment()
