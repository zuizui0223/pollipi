#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from pollipi_analysis.controlled_real_plan import DEFAULT_PLAN_SEED, write_plan_bundle


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Freeze a deterministic V3–TNOA controlled-real trial plan")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--experiment-id", required=True)
    p.add_argument("--recording-day", required=True)
    p.add_argument("--setup-id", required=True)
    p.add_argument("--target-truth-schedule-id", required=True)
    p.add_argument("--nuisance-truth-schedule-id", required=True)
    p.add_argument("--primary-source-id", required=True)
    p.add_argument("--nuisance-reference-source-id", required=True)
    p.add_argument("--nuisance-truth-source-id", required=True)
    p.add_argument("--target-truth-source-id", required=True)
    p.add_argument("--frame-interval-s", type=float, required=True)
    p.add_argument("--seed", type=int, default=DEFAULT_PLAN_SEED)
    p.add_argument("--development-per-cell", type=int, default=12)
    p.add_argument("--heldout-per-cell", type=int, default=24)
    return p.parse_args()


def main() -> None:
    a = parse_args()
    result = write_plan_bundle(
        output_dir=a.output_dir,
        experiment_id=a.experiment_id,
        recording_day=a.recording_day,
        setup_id=a.setup_id,
        target_truth_schedule_id=a.target_truth_schedule_id,
        nuisance_truth_schedule_id=a.nuisance_truth_schedule_id,
        primary_source_id=a.primary_source_id,
        nuisance_reference_source_id=a.nuisance_reference_source_id,
        nuisance_truth_source_id=a.nuisance_truth_source_id,
        target_truth_source_id=a.target_truth_source_id,
        frame_interval_s=a.frame_interval_s,
        seed=a.seed,
        n_development_per_cell=a.development_per_cell,
        n_heldout_per_cell=a.heldout_per_cell,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
