"""Auditable field-validation bundle tests."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from pollipi_analysis.replay.bundle import build_field_validation_bundle


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_valid_inputs(tmp_path: Path) -> Path:
    probe = tmp_path / "probe.csv"
    visits = tmp_path / "visits.csv"
    manifest = tmp_path / "manifest.csv"
    t0 = datetime(2026, 9, 28, 9, 0, 0)

    with probe.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "probe_timestamp",
                "decision_state",
                "actual_highres_saved",
                "record_kind",
                "video_duration_sec",
            ]
        )
        for i in range(40):
            writer.writerow(
                [
                    (t0 + timedelta(seconds=5 * i)).isoformat(timespec="seconds"),
                    "no_activity",
                    "False",
                    "image",
                    "",
                ]
            )

    visits.write_text(
        "event_id,start,end,truth_source,visitor_group,reviewer_id,confidence,reference_file,notes\n"
        "V1,30,35,continuous_reference_video,bee,R01,high,reference.mp4,test event\n",
        encoding="utf-8",
    )
    manifest.write_text(
        "run_id,probe_log,visits_csv,low_interval_sec,mid_interval_sec,high_interval_sec\n"
        "run1,probe.csv,visits.csv,30,15,5\n",
        encoding="utf-8",
    )
    return manifest


def test_bundle_writes_hashed_preflight_result_and_report(tmp_path) -> None:
    manifest = _write_valid_inputs(tmp_path)
    out = tmp_path / "bundle"

    result = build_field_validation_bundle(
        manifest,
        out,
        bootstrap_reps=20,
        bootstrap_seed=11,
        random_reps=20,
        random_seed=12,
    )

    assert result.ok
    assert result.status == "complete"
    preflight = out / "pollipi_field_input_preflight_v1.json"
    validation = out / "pollipi_field_validation_v1.json"
    report = out / "pollipi_field_validation_v1.txt"
    bundle = out / "pollipi_field_validation_bundle_v1.json"
    for path in (preflight, validation, report, bundle):
        assert path.is_file()

    b = json.loads(bundle.read_text(encoding="utf-8"))
    v = json.loads(validation.read_text(encoding="utf-8"))
    p = json.loads(preflight.read_text(encoding="utf-8"))

    assert b["schema"] == "pollipi-field-validation-bundle-v1"
    assert b["status"] == "complete"
    assert len(b["bundle_fingerprint"]) == 64
    assert len(b["analysis_code"]["analysis_code_fingerprint"]) == 64
    assert b["input_fingerprint"] == p["input_fingerprint"]
    assert v["input_preflight"]["input_fingerprint"] == p["input_fingerprint"]
    assert v["analysis_code"]["analysis_code_fingerprint"] == b["analysis_code"]["analysis_code_fingerprint"]

    assert b["artifacts"]["input_preflight"]["sha256"] == _sha256(preflight)
    assert b["artifacts"]["validation_json"]["sha256"] == _sha256(validation)
    assert b["artifacts"]["validation_report"]["sha256"] == _sha256(report)


def test_bundle_fails_closed_without_independent_truth(tmp_path) -> None:
    manifest = _write_valid_inputs(tmp_path)
    visits = tmp_path / "visits.csv"
    visits.write_text(
        "event_id,start,end,truth_source\n"
        "V1,30,35,pollipi_selected_stills\n",
        encoding="utf-8",
    )
    out = tmp_path / "bundle"

    result = build_field_validation_bundle(
        manifest,
        out,
        bootstrap_reps=10,
        random_reps=10,
    )

    assert not result.ok
    assert result.status == "input_preflight_failed"
    assert (out / "pollipi_field_input_preflight_v1.json").is_file()
    bundle = out / "pollipi_field_validation_bundle_v1.json"
    assert bundle.is_file()
    assert not (out / "pollipi_field_validation_v1.json").exists()
    assert not (out / "pollipi_field_validation_v1.txt").exists()

    payload = json.loads(bundle.read_text(encoding="utf-8"))
    assert payload["status"] == "input_preflight_failed"
    assert any("invalid/non-independent truth_source" in error for error in payload["errors"])
