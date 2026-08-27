from __future__ import annotations

import csv
from datetime import datetime, timezone

import numpy as np

from pollipi_analysis.tnoa_shadow import build_tnoa_shadow_record
from visit_monitor_server.services.tnoa_shadow_log import (
    tnoa_log_path,
    write_tnoa_shadow_record,
)


def test_tnoa_shadow_log_is_per_run_and_fail_closed(tmp_path) -> None:
    run_id = "pi1_20260827T120000"
    path = tnoa_log_path(tmp_path, run_id)
    frame = np.full((6, 4), 100, dtype=np.uint8)
    record = build_tnoa_shadow_record(
        None,
        frame,
        expected_probe_interval_sec=5.0,
        actual_probe_interval_sec=5.2,
    )

    write_tnoa_shadow_record(
        path,
        run_id=run_id,
        probe_at=datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
        record=record,
        device_id="pi1",
        device_name="PolliPi 1",
        pollipi_decision_state="no_activity",
        pollipi_decision_reason="waiting_for_reference_frame",
        policy_profile_id="three_stage_default_v1",
        simulation_run_id="issue27-three-stage-baseline",
    )

    assert path.name == f"tnoa_observation_v1_{run_id}.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 1
    row = rows[0]
    assert row["schema_version"] == "tnoa-shadow-1"
    assert row["calibration_status"] == "unavailable"
    assert row["observation_state"] == "U"
    assert row["u_reason"] == "reference_frame_pending"
    assert row["would_be_action"] == "observe_only"
    assert row["action_applied"] == "False"
    assert row["absence_available"] == "False"
    assert row["policy_profile_id"] == "three_stage_default_v1"
