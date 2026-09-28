"""Input preflight and provenance tests for PolliPi field validation."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta

from pollipi_analysis.replay.preflight import preflight_field_inputs


def _write_probe(path, *, duplicate: bool = False, bad_state: bool = False) -> None:
    t0 = datetime(2026, 9, 28, 9, 0, 0)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["probe_timestamp", "decision_state"])
        for i in range(5):
            stamp = t0 + timedelta(seconds=5 * i)
            if duplicate and i == 3:
                stamp = t0 + timedelta(seconds=10)
            state = "no_activity"
            if bad_state and i == 2:
                state = "visit_yes"
            writer.writerow([stamp.isoformat(timespec="seconds"), state])


def test_valid_preflight_hashes_inputs_and_warns_on_naive_time(tmp_path) -> None:
    probe = tmp_path / "probe.csv"
    visits = tmp_path / "visits.csv"
    manifest = tmp_path / "manifest.csv"
    _write_probe(probe)
    visits.write_text("start,end\n5,10\n", encoding="utf-8")
    manifest.write_text(
        "run_id,probe_log,visits_csv,low_interval_sec,mid_interval_sec,high_interval_sec\n"
        "r1,probe.csv,visits.csv,30,15,5\n",
        encoding="utf-8",
    )

    result = preflight_field_inputs(manifest)
    payload = result.as_dict()

    assert result.ok
    assert len(result.runs) == 1
    assert result.runs[0].probe_rows == 5
    assert result.runs[0].visit_events == 1
    assert len(result.runs[0].probe_sha256) == 64
    assert len(result.runs[0].visits_sha256) == 64
    assert len(result.input_fingerprint) == 64
    assert payload["schema"] == "pollipi-field-input-preflight-v1"
    assert any("timezone-naive" in warning for warning in result.warnings)


def test_fingerprint_changes_when_truth_file_changes(tmp_path) -> None:
    probe = tmp_path / "probe.csv"
    visits = tmp_path / "visits.csv"
    manifest = tmp_path / "manifest.csv"
    _write_probe(probe)
    visits.write_text("start,end\n5,10\n", encoding="utf-8")
    manifest.write_text(
        "run_id,probe_log,visits_csv\nr1,probe.csv,visits.csv\n",
        encoding="utf-8",
    )

    first = preflight_field_inputs(manifest)
    visits.write_text("start,end\n5,10\n15,20\n", encoding="utf-8")
    second = preflight_field_inputs(manifest)

    assert first.input_fingerprint != second.input_fingerprint
    assert first.runs[0].visits_sha256 != second.runs[0].visits_sha256


def test_preflight_fails_duplicate_probe_timestamp(tmp_path) -> None:
    probe = tmp_path / "probe.csv"
    visits = tmp_path / "visits.csv"
    manifest = tmp_path / "manifest.csv"
    _write_probe(probe, duplicate=True)
    visits.write_text("start,end\n5,10\n", encoding="utf-8")
    manifest.write_text(
        "run_id,probe_log,visits_csv\nr1,probe.csv,visits.csv\n",
        encoding="utf-8",
    )

    result = preflight_field_inputs(manifest)
    assert not result.ok
    assert any("duplicate probe timestamps" in error for error in result.errors)


def test_preflight_fails_unknown_state_and_out_of_range_visit(tmp_path) -> None:
    probe = tmp_path / "probe.csv"
    visits = tmp_path / "visits.csv"
    manifest = tmp_path / "manifest.csv"
    _write_probe(probe, bad_state=True)
    visits.write_text("start,end\n5,50\n", encoding="utf-8")
    manifest.write_text(
        "run_id,probe_log,visits_csv\nr1,probe.csv,visits.csv\n",
        encoding="utf-8",
    )

    result = preflight_field_inputs(manifest)
    assert not result.ok
    assert any("invalid decision_state" in error for error in result.errors)

    _write_probe(probe, bad_state=False)
    result = preflight_field_inputs(manifest)
    assert not result.ok
    assert any("outside the probe opportunity range" in error for error in result.errors)


def test_preflight_rejects_invalid_interval_order(tmp_path) -> None:
    probe = tmp_path / "probe.csv"
    visits = tmp_path / "visits.csv"
    manifest = tmp_path / "manifest.csv"
    _write_probe(probe)
    visits.write_text("start,end\n5,10\n", encoding="utf-8")
    manifest.write_text(
        "run_id,probe_log,visits_csv,low_interval_sec,mid_interval_sec,high_interval_sec\n"
        "r1,probe.csv,visits.csv,10,15,5\n",
        encoding="utf-8",
    )

    result = preflight_field_inputs(manifest)
    assert not result.ok
    assert any("expected high <= mid < low" in error for error in result.errors)


def test_overlapping_visits_are_warning_not_error(tmp_path) -> None:
    probe = tmp_path / "probe.csv"
    visits = tmp_path / "visits.csv"
    manifest = tmp_path / "manifest.csv"
    _write_probe(probe)
    visits.write_text("start,end\n5,12\n10,15\n", encoding="utf-8")
    manifest.write_text(
        "run_id,probe_log,visits_csv\nr1,probe.csv,visits.csv\n",
        encoding="utf-8",
    )

    result = preflight_field_inputs(manifest)
    assert result.ok
    assert any("overlapping/concurrent" in warning for warning in result.warnings)
