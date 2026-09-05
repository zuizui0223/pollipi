#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from pollipi_analysis.controlled_real_plan import DEFAULT_PLAN_SEED, write_plan_bundle

SETUP_ID = "controlled-real-bench-v1"
PRIMARY_SOURCE_ID = "fixed-camera-primary-v1"
NUISANCE_REFERENCE_SOURCE_ID = "target-free-reference-roi-v1"
NUISANCE_TRUTH_SOURCE_ID = "nuisance-controller-log-v1"
TARGET_TRUTH_SOURCE_ID = "target-controller-log-v1"
TARGET_TRUTH_SCHEDULE_ID = "target-schedule-v1"
NUISANCE_TRUTH_SCHEDULE_ID = "nuisance-schedule-v1"
FRAME_INTERVAL_S = 0.5


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate the frozen standard controlled-real bench v1 plan bundle")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--recording-day", required=True, help="Prospective recording day, e.g. 2026-09-06")
    p.add_argument("--experiment-id", default="v3-tnoa-controlled-real-bench-v1")
    p.add_argument("--seed", type=int, default=DEFAULT_PLAN_SEED)
    return p.parse_args()


def main() -> None:
    a = parse_args()
    result = write_plan_bundle(
        output_dir=a.output_dir,
        experiment_id=a.experiment_id,
        recording_day=a.recording_day,
        setup_id=SETUP_ID,
        target_truth_schedule_id=TARGET_TRUTH_SCHEDULE_ID,
        nuisance_truth_schedule_id=NUISANCE_TRUTH_SCHEDULE_ID,
        primary_source_id=PRIMARY_SOURCE_ID,
        nuisance_reference_source_id=NUISANCE_REFERENCE_SOURCE_ID,
        nuisance_truth_source_id=NUISANCE_TRUTH_SOURCE_ID,
        target_truth_source_id=TARGET_TRUTH_SOURCE_ID,
        frame_interval_s=FRAME_INTERVAL_S,
        seed=a.seed,
        n_development_per_cell=12,
        n_heldout_per_cell=24,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
