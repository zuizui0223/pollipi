from __future__ import annotations

import csv
import json
from pathlib import Path

from pollipi_analysis.controlled_real_plan import (
    generate_balanced_trial_plan,
    manifest_for_role,
    trial_plan_sha256,
    write_plan_bundle,
)
from pollipi_analysis.controlled_real_v3_tnoa import validate_manifest, validate_trial_plan


def _kwargs() -> dict[str, object]:
    return {
        "experiment_id": "bench-001",
        "recording_day": "2026-09-05",
        "setup_id": "setup-a",
        "target_truth_schedule_id": "target-schedule-v1",
        "nuisance_truth_schedule_id": "nuisance-schedule-v1",
        "seed": 20260908,
        "n_development_per_cell": 12,
        "n_heldout_per_cell": 24,
    }


def test_plan_is_deterministic_and_balanced() -> None:
    a = generate_balanced_trial_plan(**_kwargs())
    b = generate_balanced_trial_plan(**_kwargs())
    assert a == b
    assert trial_plan_sha256(a) == trial_plan_sha256(b)
    assert validate_trial_plan(a) == []
    assert len(a) == (12 + 24) * 10


def test_seed_changes_order_not_factorial_validity() -> None:
    a = generate_balanced_trial_plan(**_kwargs())
    kwargs = _kwargs(); kwargs["seed"] = 20260909
    b = generate_balanced_trial_plan(**kwargs)
    assert [row["trial_id"] for row in a] == [row["trial_id"] for row in b]
    assert [(row["target_state"], row["nuisance_family"]) for row in a] != [(row["target_state"], row["nuisance_family"]) for row in b]
    assert validate_trial_plan(b) == []


def test_manifest_builder_preserves_frozen_contract_and_truth_separation() -> None:
    manifest = manifest_for_role(
        experiment_id="bench-001",
        prospective_role="development",
        setup_id="setup-a",
        primary_source_id="camera-primary",
        nuisance_reference_source_id="reference-roi",
        nuisance_truth_source_id="nuisance-controller-log",
        target_truth_source_id="target-controller-log",
        frame_interval_s=1.0,
    )
    assert validate_manifest(manifest) == []
    assert manifest["representation_activity_score"] == "target_free_reference_temporal_rms_v1"
    assert manifest["nuisance_truth_source_id"] != manifest["nuisance_reference_source_id"]


def test_write_plan_bundle_links_manifests_to_plan_hash(tmp_path: Path) -> None:
    result = write_plan_bundle(
        output_dir=tmp_path,
        experiment_id="bench-001",
        recording_day="2026-09-05",
        setup_id="setup-a",
        target_truth_schedule_id="target-schedule-v1",
        nuisance_truth_schedule_id="nuisance-schedule-v1",
        primary_source_id="camera-primary",
        nuisance_reference_source_id="reference-roi",
        nuisance_truth_source_id="nuisance-controller-log",
        target_truth_source_id="target-controller-log",
        frame_interval_s=1.0,
    )
    with (tmp_path / "trial_plan.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 360
    assert all(row["target_truth_schedule_id"] == "target-schedule-v1" for row in rows)
    assert all(row["nuisance_truth_schedule_id"] == "nuisance-schedule-v1" for row in rows)
    development = json.loads((tmp_path / "development_manifest.json").read_text(encoding="utf-8"))
    heldout = json.loads((tmp_path / "heldout_manifest.json").read_text(encoding="utf-8"))
    assert development["trial_plan_sha256"] == result["sha256"]
    assert heldout["trial_plan_sha256"] == result["sha256"]
    assert development["prospective_role"] == "development"
    assert heldout["prospective_role"] == "heldout"
