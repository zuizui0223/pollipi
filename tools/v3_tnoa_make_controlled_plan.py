#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from pollipi_analysis.controlled_real_plan import DEFAULT_PLAN_SEED, write_plan_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze a deterministic V3–TNOA controlled-real trial plan")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--recording-day", required=True)
    parser.add_argument("--setup-id", required=True)
    parser.add_argument("--truth-schedule-id", required=True)
    parser.add_argument("--primary-source-id", required=True)
    parser.add_argument("--nuisance-reference-source-id", required=True)
    parser.add_argument("--target-truth-source-id", required=True)
    parser.add_argument("--frame-interval-s", type=float, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_PLAN_SEED)
    parser.add_argument("--development-per-cell", type=int, default=12)
    parser.add_argument("--heldout-per-cell", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = write_plan_bundle(
        output_dir=args.output_dir,
        experiment_id=args.experiment_id,
        recording_day=args.recording_day,
        setup_id=args.setup_id,
        truth_schedule_id=args.truth_schedule_id,
        primary_source_id=args.primary_source_id,
        nuisance_reference_source_id=args.nuisance_reference_source_id,
        target_truth_source_id=args.target_truth_source_id,
        frame_interval_s=args.frame_interval_s,
        seed=args.seed,
        n_development_per_cell=args.development_per_cell,
        n_heldout_per_cell=args.heldout_per_cell,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
