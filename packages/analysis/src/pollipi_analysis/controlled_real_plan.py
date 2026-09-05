"""Deterministic pre-data planner for the controlled-real V3–TNOA benchmark."""
from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Iterable

from .controlled_real_v3_tnoa import NUISANCE_FAMILIES, SCHEMA, TARGET_STATES

DEFAULT_PLAN_SEED = 20260908


def generate_balanced_trial_plan(
    *,
    experiment_id: str,
    recording_day: str,
    setup_id: str,
    truth_schedule_id: str,
    seed: int = DEFAULT_PLAN_SEED,
    n_development_per_cell: int = 12,
    n_heldout_per_cell: int = 24,
) -> list[dict[str, object]]:
    """Generate balanced randomized rounds without using any observed outcomes."""

    if not experiment_id.strip() or not recording_day.strip() or not setup_id.strip() or not truth_schedule_id.strip():
        raise ValueError("experiment_id, recording_day, setup_id and truth_schedule_id must be non-empty")
    if n_development_per_cell <= 0 or n_heldout_per_cell <= 0:
        raise ValueError("per-cell counts must be positive")

    rng = random.Random(int(seed))
    rows: list[dict[str, object]] = []
    roles = (
        ("development", int(n_development_per_cell)),
        ("heldout", int(n_heldout_per_cell)),
    )

    for role, rounds in roles:
        for round_index in range(rounds):
            cells = [(target, nuisance) for target in TARGET_STATES for nuisance in NUISANCE_FAMILIES]
            rng.shuffle(cells)
            block_id = f"{role}-round-{round_index:02d}"
            for order_in_block, (target, nuisance) in enumerate(cells):
                rows.append(
                    {
                        "trial_id": f"{experiment_id}-{role}-{round_index:02d}-{order_in_block:02d}",
                        "prospective_role": role,
                        "target_state": target,
                        "nuisance_family": nuisance,
                        "recording_day": recording_day,
                        "setup_id": setup_id,
                        "block_id": block_id,
                        "order_in_block": order_in_block,
                        "truth_schedule_id": truth_schedule_id,
                        "plan_seed": int(seed),
                    }
                )
    return rows


def manifest_for_role(
    *,
    experiment_id: str,
    prospective_role: str,
    setup_id: str,
    primary_source_id: str,
    nuisance_reference_source_id: str,
    target_truth_source_id: str,
    frame_interval_s: float,
    plan_seed: int = DEFAULT_PLAN_SEED,
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "experiment_id": experiment_id,
        "prospective_role": prospective_role,
        "setup_id": setup_id,
        "primary_source_id": primary_source_id,
        "nuisance_reference_source_id": nuisance_reference_source_id,
        "target_truth_source_id": target_truth_source_id,
        "frame_interval_s": float(frame_interval_s),
        "sequence_length": 9,
        "temporal_rank": 3,
        "alpha_representation": 0.05,
        "alpha_semantic": 0.05,
        "heldout_scoring_allowed": False,
        "plan_seed": int(plan_seed),
        "representation_activity_score": "target_free_reference_temporal_rms_v1",
        "representation_entitlement_rule": "strict_score_gt_development_threshold",
    }


def canonical_trial_plan_bytes(rows: Iterable[dict[str, object]]) -> bytes:
    payload = list(rows)
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def trial_plan_sha256(rows: Iterable[dict[str, object]]) -> str:
    return hashlib.sha256(canonical_trial_plan_bytes(rows)).hexdigest()


def write_plan_bundle(
    *,
    output_dir: str | Path,
    experiment_id: str,
    recording_day: str,
    setup_id: str,
    truth_schedule_id: str,
    primary_source_id: str,
    nuisance_reference_source_id: str,
    target_truth_source_id: str,
    frame_interval_s: float,
    seed: int = DEFAULT_PLAN_SEED,
    n_development_per_cell: int = 12,
    n_heldout_per_cell: int = 24,
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows = generate_balanced_trial_plan(
        experiment_id=experiment_id,
        recording_day=recording_day,
        setup_id=setup_id,
        truth_schedule_id=truth_schedule_id,
        seed=seed,
        n_development_per_cell=n_development_per_cell,
        n_heldout_per_cell=n_heldout_per_cell,
    )
    digest = trial_plan_sha256(rows)

    csv_path = out / "trial_plan.csv"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    for role in ("development", "heldout"):
        manifest = manifest_for_role(
            experiment_id=experiment_id,
            prospective_role=role,
            setup_id=setup_id,
            primary_source_id=primary_source_id,
            nuisance_reference_source_id=nuisance_reference_source_id,
            target_truth_source_id=target_truth_source_id,
            frame_interval_s=frame_interval_s,
            plan_seed=seed,
        )
        manifest["trial_plan_sha256"] = digest
        (out / f"{role}_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    (out / "PLAN_SHA256.txt").write_text(f"{digest}  trial_plan.canonical.json\n", encoding="utf-8")
    return {
        "trial_plan_csv": str(csv_path),
        "development_manifest": str(out / "development_manifest.json"),
        "heldout_manifest": str(out / "heldout_manifest.json"),
        "sha256": digest,
    }
