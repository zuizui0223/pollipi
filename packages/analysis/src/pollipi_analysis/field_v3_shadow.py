"""Pure intake/validation helpers for the V3 real-data shadow audit.

This module does not access a camera and does not score biological outcomes. It
validates an already-recorded fixed-interval frame ledger against the prospective
collection manifest defined in docs/LATENT_DISTURBANCE_V3_FIELD_SHADOW_AUDIT.md.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = "pollipi-latent-disturbance-v3-field-collection-v1"
FRAME_SCHEMA = "pollipi-latent-disturbance-v3-field-frame-v1"
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
WINDOW_LENGTH = 9
TEMPORAL_RANK = 3


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_roi(value: str) -> tuple[int, int, int, int]:
    try:
        parts = tuple(int(x.strip()) for x in value.split(","))
    except ValueError as exc:
        raise ValueError("reference ROI must be x0,y0,x1,y1 integers") from exc
    if len(parts) != 4:
        raise ValueError("reference ROI must contain exactly four integers")
    validate_roi(parts, FRAME_WIDTH, FRAME_HEIGHT)
    return parts


def validate_roi(roi: tuple[int, int, int, int] | list[int], width: int, height: int) -> None:
    if len(roi) != 4:
        raise ValueError("ROI must have four coordinates")
    x0, y0, x1, y1 = map(int, roi)
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError(f"ROI {tuple(roi)} lies outside {width}x{height} or has non-positive area")


def read_frame_ledger(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _parse_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid ISO timestamp: {value}") from exc


def validate_collection(
    manifest_path: str | Path,
    frame_ledger_path: str | Path,
    *,
    require_truth_ready: bool = False,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    frame_ledger_path = Path(frame_ledger_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = read_frame_ledger(frame_ledger_path)
    errors: list[str] = []
    warnings: list[str] = []

    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("manifest_schema_mismatch")
    if manifest.get("prospective_role") not in {"development", "heldout"}:
        errors.append("invalid_prospective_role")
    if manifest.get("live_adaptive_actions") is not False:
        errors.append("live_adaptive_actions_must_be_false")
    if manifest.get("truth_reference_expected") is not True:
        errors.append("independent_truth_reference_not_predeclared")
    if manifest.get("nuisance_reference_mode") != "within_frame_roi":
        errors.append("unsupported_nuisance_reference_mode")
    if manifest.get("window_length") != WINDOW_LENGTH:
        errors.append("window_length_not_frozen_v3_value")
    if manifest.get("temporal_rank") != TEMPORAL_RANK:
        errors.append("temporal_rank_not_frozen_v3_value")

    roi = manifest.get("nuisance_reference_roi")
    try:
        validate_roi(roi, int(manifest.get("frame_width", 0)), int(manifest.get("frame_height", 0)))
    except Exception:
        errors.append("invalid_nuisance_reference_roi")

    declared_count = int(manifest.get("frame_count", -1))
    if declared_count < WINDOW_LENGTH:
        errors.append("declared_frame_count_below_window_length")
    if len(rows) != declared_count:
        errors.append("frame_count_mismatch")
    if len(rows) < WINDOW_LENGTH:
        errors.append("insufficient_frames")

    collection_id = str(manifest.get("collection_id", ""))
    timestamps: list[datetime] = []
    monotonic: list[float] = []
    seen_indices: set[int] = set()
    root = frame_ledger_path.parent
    expected_dims = (int(manifest.get("frame_width", 0)), int(manifest.get("frame_height", 0)))

    for row in rows:
        if row.get("schema_version") != FRAME_SCHEMA:
            errors.append("frame_schema_mismatch")
            break
        if row.get("collection_id") != collection_id:
            errors.append("frame_collection_id_mismatch")
            break
        try:
            idx = int(row["frame_index"])
            if idx in seen_indices:
                errors.append("duplicate_frame_index")
            seen_indices.add(idx)
            timestamps.append(_parse_iso(row["captured_at"]))
            monotonic.append(float(row["monotonic_sec"]))
            if (int(row["width"]), int(row["height"])) != expected_dims:
                errors.append("frame_dimension_mismatch")
                break
        except (KeyError, ValueError):
            errors.append("invalid_frame_ledger_row")
            break

        rel = row.get("filename", "")
        frame_path = root / rel
        if not frame_path.is_file():
            errors.append("missing_frame_file")
            break
        if sha256_file(frame_path) != row.get("sha256"):
            errors.append("frame_sha256_mismatch")
            break

    if rows and seen_indices != set(range(len(rows))):
        errors.append("noncontiguous_frame_indices")

    if any(b <= a for a, b in zip(timestamps, timestamps[1:])):
        errors.append("timestamps_not_strictly_increasing")
    if any(b <= a for a, b in zip(monotonic, monotonic[1:])):
        errors.append("monotonic_times_not_strictly_increasing")

    declared_interval = float(manifest.get("probe_interval_sec", 0.0))
    max_error = float(manifest.get("max_timing_error_sec", -1.0))
    timing_errors: list[float] = []
    if declared_interval <= 0 or max_error < 0:
        errors.append("invalid_declared_timing_contract")
    elif len(monotonic) >= 2:
        timing_errors = [abs((b - a) - declared_interval) for a, b in zip(monotonic, monotonic[1:])]
        if max(timing_errors, default=0.0) > max_error:
            errors.append("timing_error_exceeds_prospective_bound")

    truth_recorded = manifest.get("truth_reference_recorded") is True
    if require_truth_ready and not truth_recorded:
        errors.append("independent_truth_reference_not_verified")
    if not truth_recorded:
        warnings.append("phase_b_truth_preparation_blocked_until_truth_reference_verified")

    structural = not errors
    return {
        "schema": "pollipi-latent-disturbance-v3-field-intake-v1",
        "collection_id": collection_id,
        "prospective_role": manifest.get("prospective_role"),
        "n_frames": len(rows),
        "n_complete_nonoverlap_windows": len(rows) // WINDOW_LENGTH,
        "max_observed_timing_error_sec": max(timing_errors, default=None),
        "structurally_valid_field_shadow_collection": structural,
        "suitable_for_v3_window_preparation": structural,
        "suitable_for_phase_b_truth_preparation": structural and truth_recorded,
        "heldout_scoring_allowed": False,
        "errors": errors,
        "warnings": warnings,
        "claim_boundary": (
            "Intake validation only. Passing does not establish V3 field accuracy and does not license "
            "heldout scoring or live adaptive capture."
        ),
    }
