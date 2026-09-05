import csv
import hashlib
import json
from pathlib import Path

from pollipi_analysis.field_v3_shadow import (
    FRAME_HEIGHT,
    FRAME_SCHEMA,
    FRAME_WIDTH,
    MANIFEST_SCHEMA,
    parse_roi,
    validate_collection,
)


def _write_pgm(path: Path, value: int) -> str:
    data = bytes([value]) * (FRAME_WIDTH * FRAME_HEIGHT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"P5\n{FRAME_WIDTH} {FRAME_HEIGHT}\n255\n".encode() + data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, n=9, truth_recorded=False, bad_timing=False):
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "collection_id": "dev001",
        "prospective_role": "development",
        "recording_day": "2026-09-05",
        "site_id": "site",
        "focal_scene_id": "scene",
        "recording_block": "block01",
        "comparison_session_id": "cmp01",
        "primary_device_id": "pi01",
        "frame_width": FRAME_WIDTH,
        "frame_height": FRAME_HEIGHT,
        "frame_count": n,
        "probe_interval_sec": 5.0,
        "max_timing_error_sec": 0.5,
        "window_length": 9,
        "temporal_rank": 3,
        "nuisance_reference_mode": "within_frame_roi",
        "nuisance_reference_roi": [400, 30, 620, 220],
        "truth_reference_expected": True,
        "truth_reference_recorded": truth_recorded,
        "live_adaptive_actions": False,
    }
    mp = tmp_path / "collection_manifest.json"
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    lp = tmp_path / "v3_shadow_frames.csv"
    fields = ["schema_version", "collection_id", "frame_index", "captured_at", "monotonic_sec", "filename", "sha256", "width", "height"]
    with lp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(n):
            rel = Path("frames") / f"probe_{i:06d}.pgm"
            digest = _write_pgm(tmp_path / rel, i % 255)
            mono = i * 5.0 + (1.0 if bad_timing and i >= 4 else 0.0)
            w.writerow({
                "schema_version": FRAME_SCHEMA,
                "collection_id": "dev001",
                "frame_index": i,
                "captured_at": f"2026-09-05T09:{i:02d}:00+09:00",
                "monotonic_sec": mono,
                "filename": rel.as_posix(),
                "sha256": digest,
                "width": FRAME_WIDTH,
                "height": FRAME_HEIGHT,
            })
    return mp, lp


def test_parse_roi_accepts_valid_and_rejects_invalid():
    assert parse_roi("400,30,620,220") == (400, 30, 620, 220)
    try:
        parse_roi("600,0,700,100")
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-frame ROI should fail")


def test_structural_collection_passes_but_truth_stage_stays_blocked(tmp_path):
    mp, lp = _fixture(tmp_path)
    out = validate_collection(mp, lp)
    assert out["structurally_valid_field_shadow_collection"] is True
    assert out["suitable_for_v3_window_preparation"] is True
    assert out["suitable_for_phase_b_truth_preparation"] is False
    assert out["heldout_scoring_allowed"] is False
    assert out["n_complete_nonoverlap_windows"] == 1


def test_truth_ready_requires_explicit_verified_manifest_state(tmp_path):
    mp, lp = _fixture(tmp_path, truth_recorded=True)
    out = validate_collection(mp, lp, require_truth_ready=True)
    assert out["errors"] == []
    assert out["suitable_for_phase_b_truth_preparation"] is True
    assert out["heldout_scoring_allowed"] is False


def test_hash_mismatch_fails_closed(tmp_path):
    mp, lp = _fixture(tmp_path)
    (tmp_path / "frames" / "probe_000004.pgm").write_bytes(b"tampered")
    out = validate_collection(mp, lp)
    assert "frame_sha256_mismatch" in out["errors"]
    assert out["suitable_for_v3_window_preparation"] is False


def test_timing_contract_is_prospective_and_enforced(tmp_path):
    mp, lp = _fixture(tmp_path, bad_timing=True)
    out = validate_collection(mp, lp)
    assert "timing_error_exceeds_prospective_bound" in out["errors"]
