"""Pre-data contract helpers for the controlled-real V3–TNOA benchmark.

This module does not access cameras, run V3, or score heldout outcomes.  It freezes
Layer-R representation-entitlement semantics and validates the prospective
factorial plan defined in docs/V3_TNOA_CONTROLLED_REAL_BENCHMARK.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor, sqrt
from typing import Iterable, Mapping, Sequence

import numpy as np

SCHEMA = "pollipi-v3-tnoa-controlled-real-v1"
TARGET_STATES = ("absent", "present")
NUISANCE_FAMILIES = (
    "none",
    "photometric_shared",
    "rigid_shared",
    "nonrigid_shared",
    "local_nonshared",
)
PROSPECTIVE_ROLES = ("development", "heldout")


@dataclass(frozen=True)
class EntitlementCalibration:
    threshold: float
    alpha: float
    n_development: int
    allowed_false_activations: int
    empirical_false_activation_rate: float


def reference_temporal_rms(frames: np.ndarray, *, scale: float = 255.0) -> float:
    """Return target-free reference temporal RMS activity, normalized by ``scale``.

    ``frames`` must have time on axis 0 and at least one additional sample axis.
    The score uses only deviations from each reference sample's temporal mean.
    """

    arr = np.asarray(frames, dtype=np.float64)
    if arr.ndim < 2:
        raise ValueError("frames must have time on axis 0 and at least one sample axis")
    if arr.shape[0] < 2:
        raise ValueError("at least two frames are required")
    if not np.isfinite(arr).all():
        raise ValueError("frames contain non-finite values")
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be finite and positive")

    centered = arr - arr.mean(axis=0, keepdims=True)
    return float(np.sqrt(np.mean(centered * centered)) / scale)


def calibrate_representation_entitlement(
    nuisance_off_scores: Sequence[float], *, alpha: float = 0.05
) -> EntitlementCalibration:
    """Calibrate a strict ``score > threshold`` Layer-R support rule.

    Calibration uses nuisance-off development scores only.  The returned order
    statistic guarantees that the empirical false-activation fraction on those
    calibration scores is no greater than ``alpha`` under the strict comparison.
    """

    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between 0 and 1")
    scores = np.asarray(list(nuisance_off_scores), dtype=np.float64)
    if scores.ndim != 1 or scores.size == 0:
        raise ValueError("nuisance_off_scores must be a non-empty one-dimensional sequence")
    if not np.isfinite(scores).all():
        raise ValueError("nuisance_off_scores contain non-finite values")

    ordered = np.sort(scores)
    allowed = floor(alpha * ordered.size + 1e-12)
    if allowed <= 0:
        threshold = float(ordered[-1])
    else:
        threshold = float(ordered[ordered.size - allowed - 1])

    false_activations = int(np.count_nonzero(scores > threshold))
    rate = false_activations / float(ordered.size)
    if rate > alpha + 1e-12:
        raise AssertionError("internal calibration error: empirical false activation exceeds alpha")

    return EntitlementCalibration(
        threshold=threshold,
        alpha=float(alpha),
        n_development=int(ordered.size),
        allowed_false_activations=int(allowed),
        empirical_false_activation_rate=float(rate),
    )


def representation_entitled(score: float, calibration: EntitlementCalibration) -> bool:
    if not np.isfinite(score):
        raise ValueError("score must be finite")
    return bool(float(score) > calibration.threshold)


def validate_manifest(manifest: Mapping[str, object]) -> list[str]:
    errors: list[str] = []

    required = (
        "schema",
        "experiment_id",
        "prospective_role",
        "setup_id",
        "primary_source_id",
        "nuisance_reference_source_id",
        "target_truth_source_id",
        "frame_interval_s",
        "sequence_length",
        "temporal_rank",
        "alpha_representation",
        "alpha_semantic",
        "heldout_scoring_allowed",
    )
    for key in required:
        if key not in manifest:
            errors.append(f"missing required field: {key}")

    if manifest.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA!r}")
    if not str(manifest.get("experiment_id", "")).strip():
        errors.append("experiment_id must be non-empty")
    if manifest.get("prospective_role") not in PROSPECTIVE_ROLES:
        errors.append(f"prospective_role must be one of {PROSPECTIVE_ROLES}")
    if not str(manifest.get("setup_id", "")).strip():
        errors.append("setup_id must be non-empty")

    primary = str(manifest.get("primary_source_id", "")).strip()
    nuisance = str(manifest.get("nuisance_reference_source_id", "")).strip()
    truth = str(manifest.get("target_truth_source_id", "")).strip()
    if not primary:
        errors.append("primary_source_id must be non-empty")
    if not nuisance:
        errors.append("nuisance_reference_source_id must be non-empty")
    if not truth:
        errors.append("target_truth_source_id must be non-empty")
    if nuisance and truth and nuisance == truth:
        errors.append("nuisance reference and target/process truth must be distinct sources")

    try:
        interval = float(manifest.get("frame_interval_s", 0.0))
        if not np.isfinite(interval) or interval <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("frame_interval_s must be finite and positive")

    if manifest.get("sequence_length") != 9:
        errors.append("sequence_length is frozen at 9")
    if manifest.get("temporal_rank") != 3:
        errors.append("temporal_rank is frozen at 3")

    for key in ("alpha_representation", "alpha_semantic"):
        try:
            value = float(manifest.get(key, -1.0))
        except (TypeError, ValueError):
            value = -1.0
        if abs(value - 0.05) > 1e-12:
            errors.append(f"{key} is frozen at 0.05")

    if manifest.get("heldout_scoring_allowed") is not False:
        errors.append("heldout_scoring_allowed must remain false in the acquisition contract")

    return errors


def factorial_counts(trials: Iterable[Mapping[str, object]]) -> dict[tuple[str, str, str], int]:
    counts = {
        (role, target, nuisance): 0
        for role in PROSPECTIVE_ROLES
        for target in TARGET_STATES
        for nuisance in NUISANCE_FAMILIES
    }
    for row in trials:
        key = (
            str(row.get("prospective_role", "")),
            str(row.get("target_state", "")),
            str(row.get("nuisance_family", "")),
        )
        if key in counts:
            counts[key] += 1
    return counts


def validate_trial_plan(
    trials: Sequence[Mapping[str, object]], *, min_development_per_cell: int = 12, min_heldout_per_cell: int = 24
) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    for idx, row in enumerate(trials):
        trial_id = str(row.get("trial_id", "")).strip()
        if not trial_id:
            errors.append(f"trial {idx}: trial_id must be non-empty")
        elif trial_id in seen_ids:
            errors.append(f"trial {idx}: duplicate trial_id {trial_id!r}")
        else:
            seen_ids.add(trial_id)

        role = row.get("prospective_role")
        target = row.get("target_state")
        nuisance = row.get("nuisance_family")
        if role not in PROSPECTIVE_ROLES:
            errors.append(f"trial {idx}: invalid prospective_role {role!r}")
        if target not in TARGET_STATES:
            errors.append(f"trial {idx}: invalid target_state {target!r}")
        if nuisance not in NUISANCE_FAMILIES:
            errors.append(f"trial {idx}: invalid nuisance_family {nuisance!r}")

        for field in ("recording_day", "setup_id", "block_id", "truth_schedule_id"):
            if not str(row.get(field, "")).strip():
                errors.append(f"trial {idx}: {field} must be non-empty")

    counts = factorial_counts(trials)
    for (role, target, nuisance), count in sorted(counts.items()):
        minimum = min_development_per_cell if role == "development" else min_heldout_per_cell
        if count < minimum:
            errors.append(
                f"insufficient {role} trials for target={target}, nuisance={nuisance}: "
                f"{count} < {minimum}"
            )

    return errors
