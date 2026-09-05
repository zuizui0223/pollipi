from __future__ import annotations

import numpy as np

from pollipi_analysis.controlled_real_v3_tnoa import (
    NUISANCE_FAMILIES,
    TARGET_STATES,
    calibrate_representation_entitlement,
    reference_temporal_rms,
    representation_entitled,
    validate_manifest,
    validate_trial_plan,
)


def _manifest() -> dict[str, object]:
    return {
        "schema": "pollipi-v3-tnoa-controlled-real-v2",
        "experiment_id": "bench-001",
        "prospective_role": "development",
        "setup_id": "setup-a",
        "primary_source_id": "camera-primary",
        "nuisance_reference_source_id": "roi-reference",
        "nuisance_truth_source_id": "nuisance-controller-log",
        "target_truth_source_id": "target-controller-log",
        "frame_interval_s": 1.0,
        "sequence_length": 9,
        "temporal_rank": 3,
        "alpha_representation": 0.05,
        "alpha_semantic": 0.05,
        "heldout_scoring_allowed": False,
    }


def _full_trial_plan() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for role, minimum in (("development", 12), ("heldout", 24)):
        for target in TARGET_STATES:
            for nuisance in NUISANCE_FAMILIES:
                for rep in range(minimum):
                    rows.append({
                        "trial_id": f"{role}-{target}-{nuisance}-{rep:02d}",
                        "prospective_role": role,
                        "target_state": target,
                        "nuisance_family": nuisance,
                        "recording_day": "2026-09-05",
                        "setup_id": "setup-a",
                        "block_id": f"block-{rep:02d}",
                        "target_truth_schedule_id": "target-schedule-v1",
                        "nuisance_truth_schedule_id": "nuisance-schedule-v1",
                    })
    return rows


def test_reference_temporal_rms_static_is_zero_and_motion_is_positive() -> None:
    static = np.full((9, 4, 5), 128, dtype=np.uint8)
    moving = static.copy(); moving[4:, :, :] = 160
    assert reference_temporal_rms(static) == 0.0
    assert reference_temporal_rms(moving) > 0.0


def test_entitlement_calibration_respects_empirical_alpha() -> None:
    scores = [i / 100.0 for i in range(20)]
    calibration = calibrate_representation_entitlement(scores, alpha=0.05)
    empirical = sum(representation_entitled(score, calibration) for score in scores) / len(scores)
    assert empirical <= 0.05
    assert calibration.empirical_false_activation_rate == empirical


def test_manifest_requires_truth_reference_separation() -> None:
    manifest = _manifest()
    assert validate_manifest(manifest) == []
    manifest["nuisance_truth_source_id"] = manifest["nuisance_reference_source_id"]
    assert any("nuisance reference and nuisance truth" in e for e in validate_manifest(manifest))
    manifest = _manifest(); manifest["target_truth_source_id"] = manifest["nuisance_reference_source_id"]
    assert any("nuisance reference and target/process truth" in e for e in validate_manifest(manifest))


def test_manifest_freezes_v3_and_risk_semantics() -> None:
    manifest = _manifest(); manifest["temporal_rank"] = 4; manifest["alpha_semantic"] = 0.10; manifest["heldout_scoring_allowed"] = True
    errors = validate_manifest(manifest)
    assert "temporal_rank is frozen at 3" in errors
    assert "alpha_semantic is frozen at 0.05" in errors
    assert "heldout_scoring_allowed must remain false in the acquisition contract" in errors


def test_full_factorial_trial_plan_passes() -> None:
    assert validate_trial_plan(_full_trial_plan()) == []


def test_missing_factorial_cell_fails_closed() -> None:
    trials = [row for row in _full_trial_plan() if not (row["prospective_role"] == "heldout" and row["target_state"] == "present" and row["nuisance_family"] == "local_nonshared")]
    errors = validate_trial_plan(trials)
    assert any("insufficient heldout trials for target=present, nuisance=local_nonshared" in e for e in errors)
