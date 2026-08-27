"""Build blinded annotation sheets from Pi TNOA shadow logs.

Only provenance/join fields are copied from the algorithm log.  Target/nuisance/O
scores and provisional observation states are intentionally withheld from human
truth annotators.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Mapping

from pollipi_analysis.tnoa_annotation import (
    BiologicalTruth,
    CoupledTruth,
    IndependentTruthRecord,
    NUISANCE_EFFECTS,
    NUISANCE_FAMILIES,
    ObservabilityTruth,
)

ANNOTATION_SCHEMA = "tnoa-independent-truth-1"

PROVENANCE_COLUMNS = (
    "annotation_schema",
    "window_id",
    "run_id",
    "probe_timestamp",
    "recording_day",
    "device_id",
    "record_kind",
    "saved_image_filename",
    "video_filename",
    "evidence_event_id",
    "evidence_previous_filename",
    "evidence_current_filename",
    "site_id",
    "flower_id",
    "plant_species",
    "comparison_session_id",
    "camera_role",
    "method_mode",
)

TRUTH_COLUMNS = (
    "focal_scene_id",
    "recording_block",
    "reference_source_id",
    "biological_truth",
    "coupled_truth",
    "observability_truth",
    "nuisance_families",
    "nuisance_effects",
    "annotator_id",
    "adjudicated",
)

ANNOTATION_COLUMNS = PROVENANCE_COLUMNS + TRUTH_COLUMNS

# Explicitly permitted fields from the algorithm-generated TNOA CSV.  No score,
# support, observation-state or action field is allowed through this projection.
_ALLOWED_SOURCE = frozenset({
    "run_id",
    "probe_timestamp",
    "device_id",
    "record_kind",
    "saved_image_filename",
    "video_filename",
    "evidence_event_id",
    "evidence_previous_filename",
    "evidence_current_filename",
    "site_id",
    "flower_id",
    "plant_species",
    "comparison_session_id",
    "camera_role",
    "method_mode",
})


def _date_from_timestamp(value: str) -> str:
    if not value:
        return ""
    return datetime.fromisoformat(value).date().isoformat()


def blank_annotation_row(source: Mapping[str, str]) -> dict[str, str]:
    run_id = str(source.get("run_id", ""))
    probe_timestamp = str(source.get("probe_timestamp", ""))
    if not run_id or not probe_timestamp:
        raise ValueError("source row requires run_id and probe_timestamp")
    row = {key: "" for key in ANNOTATION_COLUMNS}
    row["annotation_schema"] = ANNOTATION_SCHEMA
    row["window_id"] = f"{run_id}|{probe_timestamp}"
    row["recording_day"] = _date_from_timestamp(probe_timestamp)
    for key in _ALLOWED_SOURCE:
        if key in row:
            row[key] = str(source.get(key, "") or "")
    # Use run_id as a neutral default block identifier. Focal-scene identity must
    # still be supplied independently before the sheet is considered complete.
    row["recording_block"] = run_id
    row["adjudicated"] = "False"
    return row


def build_blank_annotation_rows(rows: Iterable[Mapping[str, str]]) -> list[dict[str, str]]:
    return [blank_annotation_row(row) for row in rows]


def _split_set(value: str) -> frozenset[str]:
    return frozenset(x.strip() for x in str(value).split(";") if x.strip())


def parse_completed_annotation(row: Mapping[str, str]) -> IndependentTruthRecord:
    if row.get("annotation_schema") != ANNOTATION_SCHEMA:
        raise ValueError("unexpected annotation schema")
    biological = BiologicalTruth(str(row.get("biological_truth", "")))
    coupled = CoupledTruth(str(row.get("coupled_truth", "")))
    observability = ObservabilityTruth(str(row.get("observability_truth", "")))
    nuisance_families = _split_set(str(row.get("nuisance_families", "")))
    nuisance_effects = _split_set(str(row.get("nuisance_effects", "")))
    unknown_families = set(nuisance_families) - NUISANCE_FAMILIES
    if unknown_families:
        raise ValueError(f"unknown nuisance families: {sorted(unknown_families)}")
    unknown_effects = set(nuisance_effects) - NUISANCE_EFFECTS
    if unknown_effects:
        raise ValueError(f"unknown nuisance effects: {sorted(unknown_effects)}")
    return IndependentTruthRecord(
        window_id=str(row.get("window_id", "")),
        recording_day=str(row.get("recording_day", "")),
        focal_scene_id=str(row.get("focal_scene_id", "")),
        recording_block=str(row.get("recording_block", "")),
        reference_source_id=str(row.get("reference_source_id", "")),
        biological_truth=biological,
        coupled_truth=coupled,
        observability_truth=observability,
        nuisance_families=nuisance_families,
        nuisance_effects=nuisance_effects,
        annotator_id=str(row.get("annotator_id", "")),
        adjudicated=str(row.get("adjudicated", "")).strip().lower() in {"1", "true", "yes", "y"},
    )
