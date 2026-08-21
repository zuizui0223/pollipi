import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import pollipi_analysis.simulation.v7_artifact_adapter as adapter


def _write_dummy_artifact(tmp_path):
    backgrounds = np.zeros((2, 96, 128), dtype=np.uint8)
    frames = np.ones((2, 96, 128), dtype=np.uint8) * 10
    metadata = [
        {
            "condition_id": f"dummy-{index}",
            "family": "clean",
            "tier": 0,
            "replicate": index,
            "seed": 100 + index,
            "true_visit": bool(index),
            "event_visibility": 1.0,
            "intensity": 0.45,
        }
        for index in range(2)
    ]
    npz = tmp_path / "dummy.npz"
    np.savez_compressed(
        npz,
        backgrounds=backgrounds,
        frames=frames,
        metadata_json=np.array(json.dumps(metadata, sort_keys=True, separators=(",", ":"))),
    )
    digest = hashlib.sha256(npz.read_bytes()).hexdigest()
    manifest = tmp_path / "dummy.json"
    manifest.write_text(json.dumps({
        "schema": adapter.ARTIFACT_SCHEMA,
        "world_spec_sha256": "a" * 64,
        "world_fingerprint": "b" * 64,
        "condition_count": 2,
        "shape": [96, 128],
        "npz_sha256": digest,
    }), encoding="utf-8")
    return npz, manifest


def test_adapter_passes_only_pixels_to_analyze_and_attaches_truth_afterward(tmp_path, monkeypatch):
    npz, manifest = _write_dummy_artifact(tmp_path)
    calls = []

    def fake_analyze(frame, background):
        calls.append((frame.copy(), background.copy()))
        return SimpleNamespace(
            state="no_activity",
            reason="dummy",
            features=SimpleNamespace(
                global_synchrony=0.1,
                active_cell_proportion=0.2,
                estimated_global_shift=0.3,
            ),
        )

    monkeypatch.setattr(adapter, "analyze", fake_analyze)
    loaded, rows = adapter.run_v7_artifact(
        npz,
        manifest,
        expected_world_spec_sha256="a" * 64,
    )
    assert loaded.condition_count == 2
    assert len(calls) == 2
    assert len(rows) == 2
    assert rows[0].true_visit is False
    assert rows[1].true_visit is True
    assert np.array_equal(calls[0][0], np.ones((96, 128), dtype=np.uint8) * 10)
    assert np.array_equal(calls[0][1], np.zeros((96, 128), dtype=np.uint8))


def test_adapter_rejects_tampered_pixel_artifact(tmp_path):
    npz, manifest = _write_dummy_artifact(tmp_path)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["npz_sha256"] = "0" * 64
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        adapter.read_v7_artifact(npz, manifest)
