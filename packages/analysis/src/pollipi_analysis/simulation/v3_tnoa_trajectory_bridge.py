"""Fresh V3–TNOA bridge using pre-existing shadow trajectory target evidence.

Protocol: ``docs/V3_TNOA_TRAJECTORY_BRIDGE.md``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.shadow import _trajectory_features
from pollipi_analysis.simulation import latent_disturbance_v3_temporal_subspace as v3
from pollipi_analysis.simulation.v3_tnoa_bridge import (
    ALPHA,
    ARMS,
    MIXED_SCENARIOS,
    PINNED_TNOA_SHA,
    UNIQUE_SCENARIOS,
    _calibrate_threshold,
    _false_certainty,
    _load_tnoa,
    _metrics,
    _paired_bootstrap_difference,
    _truth_decision,
)

MASTER_SEED = 20260907
DEFAULT_N_REPS = 96
DEFAULT_DEV_REPS = 48
BOOTSTRAP_REPS = 5000
BOOTSTRAP_SEED = 2026090701

_LOCAL_STATES = frozenset({"uncertain_local_activity", "strong_visitation_candidate"})


def _trajectory_target_evaluation(frames: np.ndarray, world: v3.TemporalWorld) -> dict[str, float]:
    decisions = [analyze(frame, world.primary_background) for frame in frames]
    local_decisions = [decision for decision in decisions if decision.state in _LOCAL_STATES]
    candidate_fraction = len(local_decisions) / len(decisions)
    centroids = [
        (float(decision.features.centroid_x), float(decision.features.centroid_y))
        for decision in local_decisions
        if decision.features.centroid_x is not None and decision.features.centroid_y is not None
    ]

    if len(centroids) < 2:
        path_efficiency = 0.0
        mean_step = 0.0
        reversal_rate = 0.0
        score = 0.0
    else:
        path_eff, mean_step_value, reversal = _trajectory_features(centroids)
        path_efficiency = float(path_eff or 0.0)
        mean_step = float(mean_step_value or 0.0)
        reversal_rate = float(reversal or 0.0)
        score = float(candidate_fraction * path_efficiency * (1.0 - reversal_rate))

    environmental_noise_fraction = float(
        np.mean([decision.state == "environmental_noise" for decision in decisions])
    )
    return {
        "target_score": score,
        "candidate_fraction": float(candidate_fraction),
        "path_efficiency": path_efficiency,
        "mean_step": mean_step,
        "reversal_rate": reversal_rate,
        "environmental_noise_fraction": environmental_noise_fraction,
        "trajectory_points": len(centroids),
    }


def _arm_scores(world: v3.TemporalWorld, *, permutation_seed: int) -> dict[str, dict[str, float]]:
    raw = _trajectory_target_evaluation(world.primary_frames, world)

    matched_frames, matched_diag = v3.temporal_subspace_project(
        world.primary_frames,
        world.primary_background,
        world.reference_frames,
        world.reference_background,
    )
    matched = _trajectory_target_evaluation(matched_frames, world)

    perm = v3._permutation(permutation_seed)
    broken_frames, broken_diag = v3.temporal_subspace_project(
        world.primary_frames,
        world.primary_background,
        world.reference_frames[perm],
        world.reference_background,
    )
    broken = _trajectory_target_evaluation(broken_frames, world)

    return {
        "raw": {
            **raw,
            "nuisance_score": raw["environmental_noise_fraction"],
        },
        "matched_v3": {
            **matched,
            "nuisance_score": float(matched_diag["explained_primary_energy_fraction"]),
        },
        "time_broken_v3": {
            **broken,
            "nuisance_score": float(broken_diag["explained_primary_energy_fraction"]),
        },
    }


def _trajectory_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for scenario in v3.SCENARIOS:
        subset = [row for row in rows if row["scenario"] == scenario]
        out[scenario] = {
            "target_score_mean": float(np.mean([row["target_score"] for row in subset])),
            "candidate_fraction_mean": float(np.mean([row["candidate_fraction"] for row in subset])),
            "path_efficiency_mean": float(np.mean([row["path_efficiency"] for row in subset])),
            "reversal_rate_mean": float(np.mean([row["reversal_rate"] for row in subset])),
            "trajectory_points_mean": float(np.mean([row["trajectory_points"] for row in subset])),
        }
    return out


def evaluate_trajectory_bridge(
    *,
    n_reps: int = DEFAULT_N_REPS,
    dev_reps: int = DEFAULT_DEV_REPS,
    seed: int = MASTER_SEED,
    alpha: float = ALPHA,
    bootstrap_reps: int = BOOTSTRAP_REPS,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    pollipi_sha: str | None = None,
    tnoa_sha: str = PINNED_TNOA_SHA,
) -> dict[str, Any]:
    if n_reps <= 1:
        raise ValueError("n_reps must be > 1")
    if dev_reps <= 0 or dev_reps >= n_reps:
        raise ValueError("dev_reps must be between 1 and n_reps-1")
    if bootstrap_reps <= 0:
        raise ValueError("bootstrap_reps must be positive")

    Evidence, classify = _load_tnoa()

    score_rows: list[dict[str, Any]] = []
    for scenario_index, scenario in enumerate(v3.SCENARIOS):
        for rep in range(n_reps):
            world_seed = seed + scenario_index * 100_000 + rep
            permutation_seed = seed + 40_000_000 + scenario_index * 100_000 + rep
            world = v3.generate_temporal_world(scenario, world_seed)
            scores = _arm_scores(world, permutation_seed=permutation_seed)
            for arm, arm_scores in scores.items():
                score_rows.append(
                    {
                        "scenario": scenario,
                        "scenario_index": scenario_index,
                        "rep": rep,
                        "split": "development" if rep < dev_reps else "heldout",
                        "arm": arm,
                        **arm_scores,
                    }
                )

    calibration: dict[str, Any] = {}
    for arm in ARMS:
        dev = [row for row in score_rows if row["arm"] == arm and row["split"] == "development"]
        target_negatives = {
            scenario: [row["target_score"] for row in dev if row["scenario"] == scenario]
            for scenario in v3.NOISE_SCENARIOS
        }
        target_threshold, target_dev_rates = _calibrate_threshold(target_negatives, alpha=alpha)
        nuisance_negatives = {
            "target_only": [row["nuisance_score"] for row in dev if row["scenario"] == "target_only"]
        }
        nuisance_threshold, nuisance_dev_rates = _calibrate_threshold(nuisance_negatives, alpha=alpha)
        calibration[arm] = {
            "target_threshold": target_threshold,
            "target_development_false_support_by_family": target_dev_rates,
            "nuisance_threshold": nuisance_threshold,
            "nuisance_development_false_support": nuisance_dev_rates["target_only"],
        }

    decision_rows: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    for row in score_rows:
        arm = row["arm"]
        cal = calibration[arm]
        target_supported = bool(row["target_score"] >= cal["target_threshold"])
        nuisance_supported = bool(row["nuisance_score"] >= cal["nuisance_threshold"])
        record = classify(
            Evidence(
                deviation_observed=True,
                target_supported=target_supported,
                nuisance_supported=nuisance_supported,
                observable=True,
                coupled_response_supported=False,
                attribution_supported=False,
            )
        )
        decision_rows[arm].append(
            {
                **row,
                "target_supported": target_supported,
                "nuisance_supported": nuisance_supported,
                "decision": record.decision.value,
                "reason": record.reason.value,
                "truth_decision": _truth_decision(row["scenario"]),
                "false_certainty": _false_certainty(record.decision.value, row["scenario"]),
            }
        )

    heldout_rows = {
        arm: [row for row in rows if row["split"] == "heldout"]
        for arm, rows in decision_rows.items()
    }
    metrics = {arm: _metrics(rows) for arm, rows in heldout_rows.items()}
    trajectory = {arm: _trajectory_diagnostics(rows) for arm, rows in heldout_rows.items()}
    heldout_rep_indices = list(range(dev_reps, n_reps))

    bootstrap = {
        "matched_minus_raw_safe_unique_coverage": _paired_bootstrap_difference(
            heldout_rows["matched_v3"],
            heldout_rows["raw"],
            heldout_rep_indices,
            metric="safe_unique_coverage",
            n_bootstrap=bootstrap_reps,
            seed=bootstrap_seed,
        ),
        "matched_minus_time_broken_safe_unique_coverage": _paired_bootstrap_difference(
            heldout_rows["matched_v3"],
            heldout_rows["time_broken_v3"],
            heldout_rep_indices,
            metric="safe_unique_coverage",
            n_bootstrap=bootstrap_reps,
            seed=bootstrap_seed + 1,
        ),
        "matched_minus_raw_false_certainty": _paired_bootstrap_difference(
            heldout_rows["matched_v3"],
            heldout_rows["raw"],
            heldout_rep_indices,
            metric="pooled_false_certainty_rate",
            n_bootstrap=bootstrap_reps,
            seed=bootstrap_seed + 2,
        ),
    }

    matched = metrics["matched_v3"]
    raw = metrics["raw"]
    broken = metrics["time_broken_v3"]
    gain_raw = matched["safe_unique_coverage"] - raw["safe_unique_coverage"]
    gain_broken = matched["safe_unique_coverage"] - broken["safe_unique_coverage"]

    criteria = {
        "matched_safe_coverage_gain_vs_raw_ge_0_10": gain_raw >= 0.10,
        "matched_minus_raw_bootstrap_low_gt_0": (
            bootstrap["matched_minus_raw_safe_unique_coverage"]["ci95_low"] > 0.0
        ),
        "matched_safe_coverage_gain_vs_time_broken_ge_0_05": gain_broken >= 0.05,
        "matched_minus_time_broken_bootstrap_low_gt_0": (
            bootstrap["matched_minus_time_broken_safe_unique_coverage"]["ci95_low"] > 0.0
        ),
        "matched_false_certainty_le_0_10_and_within_raw_plus_0_01": (
            matched["pooled_false_certainty_rate"] <= 0.10 + 1e-12
            and matched["pooled_false_certainty_rate"] <= raw["pooled_false_certainty_rate"] + 0.01 + 1e-12
        ),
        "matched_target_only_T_loss_vs_raw_le_0_05": (
            matched["target_only_T_rate"] >= raw["target_only_T_rate"] - 0.05 - 1e-12
        ),
        "matched_forced_unique_overlap_within_raw_plus_0_05": (
            matched["forced_unique_overlap_rate"] <= raw["forced_unique_overlap_rate"] + 0.05 + 1e-12
        ),
    }

    return {
        "schema": "pollipi-v3-tnoa-trajectory-bridge-v1",
        "protocol": "docs/V3_TNOA_TRAJECTORY_BRIDGE.md",
        "generation_note": (
            "Post-failure target-observer revision using a fresh seed; V3, TNOA, nuisance interface, alpha and promotion gates frozen."
        ),
        "source": {
            "pollipi_sha": pollipi_sha,
            "tnoa_repo": "zuizui0223/tnoa",
            "tnoa_sha": tnoa_sha,
        },
        "design": {
            "master_seed": seed,
            "n_reps_per_scenario": n_reps,
            "development_reps": dev_reps,
            "heldout_reps": n_reps - dev_reps,
            "alpha": alpha,
            "bootstrap_reps": bootstrap_reps,
            "bootstrap_seed": bootstrap_seed,
            "sequence_length": v3.T,
            "temporal_rank": v3.TEMPORAL_RANK,
            "target_score": "candidate_fraction * path_efficiency * (1 - reversal_rate)",
            "arms": list(ARMS),
            "scenarios": list(v3.SCENARIOS),
        },
        "calibration": calibration,
        "heldout_metrics": metrics,
        "trajectory_diagnostics": trajectory,
        "paired_bootstrap": bootstrap,
        "contrasts": {
            "matched_minus_raw_safe_unique_coverage": gain_raw,
            "matched_minus_time_broken_safe_unique_coverage": gain_broken,
            "matched_minus_raw_false_certainty": (
                matched["pooled_false_certainty_rate"] - raw["pooled_false_certainty_rate"]
            ),
        },
        "promotion_rule": {
            "criteria": criteria,
            "promoted_to_joint_v3_tnoa_candidate": all(criteria.values()),
        },
        "claim_boundary": (
            "Fresh controlled synthetic trajectory bridge only. Does not establish field performance, biological absence, physical nuisance identity or universal cross-domain benefit."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-reps", type=int, default=DEFAULT_N_REPS)
    parser.add_argument("--dev-reps", type=int, default=DEFAULT_DEV_REPS)
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    parser.add_argument("--alpha", type=float, default=ALPHA)
    parser.add_argument("--bootstrap-reps", type=int, default=BOOTSTRAP_REPS)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--pollipi-sha")
    parser.add_argument("--tnoa-sha", default=PINNED_TNOA_SHA)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = evaluate_trajectory_bridge(
        n_reps=args.n_reps,
        dev_reps=args.dev_reps,
        seed=args.seed,
        alpha=args.alpha,
        bootstrap_reps=args.bootstrap_reps,
        bootstrap_seed=args.bootstrap_seed,
        pollipi_sha=args.pollipi_sha,
        tnoa_sha=args.tnoa_sha,
    )
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
