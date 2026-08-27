from __future__ import annotations

import pytest

from pollipi_analysis.tnoa_annotation import (
    BiologicalTruth,
    CoupledTruth,
    IndependentTruthRecord,
    ObservabilityTruth,
)
from pollipi_analysis.tnoa_annotation_sheet import (
    ANNOTATION_COLUMNS,
    blank_annotation_row,
    parse_completed_annotation,
)


def test_blank_sheet_hides_algorithm_evidence() -> None:
    source = {
        "run_id": "pi1_20260827T120000",
        "probe_timestamp": "2026-08-27T12:00:05+09:00",
        "device_id": "pi1",
        "record_kind": "image",
        "saved_image_filename": "image.jpg",
        "target_ordinal_score": "1.0",
        "nuisance_global_synchrony": "0.9",
        "observability_luma_mean": "100",
        "observation_state": "U",
        "u_reason": "field_calibration_pending",
        "would_be_action": "observe_only",
    }
    row = blank_annotation_row(source)
    assert tuple(row) == ANNOTATION_COLUMNS
    assert row["window_id"].startswith("pi1_20260827T120000|")
    assert row["recording_day"] == "2026-08-27"
    assert row["recording_block"] == "pi1_20260827T120000"
    assert "target_ordinal_score" not in row
    assert "nuisance_global_synchrony" not in row
    assert "observability_luma_mean" not in row
    assert "observation_state" not in row
    assert "u_reason" not in row
    assert "would_be_action" not in row


def test_completed_truth_keeps_four_layers_independent() -> None:
    row = blank_annotation_row({
        "run_id": "r1",
        "probe_timestamp": "2026-08-27T12:00:05+09:00",
        "device_id": "pi1",
    })
    row.update({
        "focal_scene_id": "flower-7",
        "reference_source_id": "refcam-A",
        "biological_truth": "visit_event",
        "coupled_truth": "present",
        "observability_truth": "compromised",
        "nuisance_families": "wind_target_motion;moving_shadow",
        "nuisance_effects": "mask;corrupt_attribution",
        "annotator_id": "A1",
    })
    record = parse_completed_annotation(row)
    assert record.biological_truth is BiologicalTruth.VISIT_EVENT
    assert record.coupled_truth is CoupledTruth.PRESENT
    assert record.observability_truth is ObservabilityTruth.COMPROMISED
    assert record.nuisance_families == frozenset({"wind_target_motion", "moving_shadow"})
    assert record.split_group == "2026-08-27|flower-7|r1"


def test_coupled_present_requires_contact_or_visit_truth() -> None:
    with pytest.raises(ValueError, match="coupled present"):
        IndependentTruthRecord(
            window_id="w1",
            recording_day="2026-08-27",
            focal_scene_id="flower-1",
            recording_block="b1",
            reference_source_id="ref1",
            biological_truth=BiologicalTruth.NO_INSECT,
            coupled_truth=CoupledTruth.PRESENT,
            observability_truth=ObservabilityTruth.OBSERVABLE,
        )


def test_truth_unresolved_is_not_absence() -> None:
    record = IndependentTruthRecord(
        window_id="w1",
        recording_day="2026-08-27",
        focal_scene_id="flower-1",
        recording_block="b1",
        reference_source_id="ref1",
        biological_truth=BiologicalTruth.TRUTH_UNRESOLVED,
        coupled_truth=CoupledTruth.UNRESOLVED,
        observability_truth=ObservabilityTruth.UNOBSERVABLE,
    )
    assert record.resolved_biological_truth is False
