"""Per-run CSV persistence for fail-closed TNOA Phase-A shadow records."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from pollipi_analysis.tnoa_shadow import TNOAShadowRecord

TNOA_SHADOW_PREFIX = "tnoa_observation_v1"

META_COLUMNS = [
    "run_id",
    "probe_timestamp",
    "device_id",
    "device_name",
    "pollipi_decision_state",
    "pollipi_decision_reason",
    "saved_image_filename",
    "evidence_event_id",
    "evidence_previous_filename",
    "evidence_current_filename",
    "policy_profile_id",
    "simulation_run_id",
]


def tnoa_log_path(image_dir: Path, run_id: str) -> Path:
    return image_dir / f"{TNOA_SHADOW_PREFIX}_{run_id}.csv"


def write_tnoa_shadow_record(
    path: Path,
    *,
    run_id: str,
    probe_at: datetime,
    record: TNOAShadowRecord,
    device_id: str,
    device_name: str,
    pollipi_decision_state: str,
    pollipi_decision_reason: str,
    saved_image_filename: str = "",
    evidence_event_id: str = "",
    evidence_previous_filename: str = "",
    evidence_current_filename: str = "",
    policy_profile_id: str = "",
    simulation_run_id: str = "",
) -> None:
    """Append one T/C/N/O/A- shadow record without changing capture behaviour."""
    flat = record.flat()
    row = {
        "run_id": run_id,
        "probe_timestamp": probe_at.isoformat(timespec="seconds"),
        "device_id": device_id,
        "device_name": device_name,
        "pollipi_decision_state": pollipi_decision_state,
        "pollipi_decision_reason": pollipi_decision_reason,
        "saved_image_filename": saved_image_filename,
        "evidence_event_id": evidence_event_id,
        "evidence_previous_filename": evidence_previous_filename,
        "evidence_current_filename": evidence_current_filename,
        "policy_profile_id": policy_profile_id,
        "simulation_run_id": simulation_run_id,
        **flat,
    }
    columns = META_COLUMNS + list(flat.keys())
    write_header = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
