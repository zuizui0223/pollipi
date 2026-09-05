"""Fresh synthetic bridge between V3 representation and reusable TNOA decisions.

Protocol: ``docs/V3_TNOA_SYNTHETIC_BRIDGE.md``.

This module intentionally imports ``tnoa`` only at execution time. The dedicated
workflow checks out a pinned TNOA repository commit and adds it to ``PYTHONPATH``.
The ordinary PolliPi analysis package therefore does not acquire a runtime TNOA
dependency.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from pollipi_analysis.simulation import latent_disturbance_v3_temporal_subspace as v3

MASTER_SEED = 20260906
DEFAULT_N_REPS = 96
DEFAULT_DEV_REPS = 48
ALPHA = 0.05
BOOTSTRAP_REPS = 5000
BOOTSTRAP_SEED = 2026090601
PINNED_TNOA_SHA = "40fa8f66132cd86bdd5294b7360e024d13f9d9c4"

ARMS = ("raw", "matched_v3", "time_broken_v3")
UNIQUE_SCENARIOS = ("target_only",) + tuple(v3.NOISE_SCENARIOS)
MIXED_SCENARIOS = tuple(v3.MIXED_TARGET_SCENARIOS)


def _load_tnoa():
    try:
        from tnoa import Evidence, classify
    except ImportError as exc:  # pragma: no cover - exercised by dedicated workflow
        raise RuntimeError(
            "TNOA is required for the V3 bridge. Add the pinned TNOA checkout to PYTHONPATH."
        ) from exc
    return Evidence, classify


def _state_scores(states: Iterable[str]) -> tuple[float, float]:
    states = list(states)
    if not states:
        raise ValueError("states must be non-empty")
    local = sum(
        state in ("uncertain_local_activity", "strong_visitation_candidate")
        for state in states
    ) / len(states)
    nuisance = sum(state == "environmental_noise" for state in states) / len(states)
    return float(local), float(nuisance)


def _arm_scores(world: v3.TemporalWorld, *, permutation_seed: int) -> dict[str, dict[str, float]]:
    raw_eval = v3._evaluate_sequence(world.primary_frames, world)
    raw_target, raw_nuisance = _state_scores(raw_eval["states"])

    matched_frames, matched_diag = v3.temporal_subspace_project(
        world.primary_frames,
        world.primary_background,
        world.reference_frames,
        world.reference_background,
    )
    matched_eval = v3._evaluate_sequence(matched_frames, world)
    matched_target, _ = _state_scores(matched_eval["states"])

    perm = v3._permutation(permutation_seed)
    broken_frames, broken_diag = v3.temporal_subspace_project(
        world.primary_frames,
        world.primary_background,
        world.reference_frames[perm],
        world.reference_background,
    )
    broken_eval = v3._evaluate_sequence(broken_frames, world)
    broken_target, _ = _state_scores(broken_eval["states"])

    return {
        "raw": {
            "target_score": raw_target,
            "nuisance_score": raw_nuisance,
        },
        "matched_v3": {
            "target_score": matched_target,
            "nuisance_score": float(matched_diag["explained_primary_energy_fraction"]),
        },
        "time_broken_v3": {
            "target_score": broken_target,
            "nuisance_score": float(broken_diag["explained_primary_energy_fraction"]),
        },
    }


def _candidate_thresholds(values: Iterable[float]) -> list[float]:
    vals = sorted({float(v) for v in values})
    if not vals:
        raise ValueError("calibration values must be non-empty")
    above_max = math.nextafter(vals[-1], math.inf)
    return vals + [above_max]


def _false_support_rate(values: Iterable[float], threshold: float) -> float:
    vals = list(values)
    if not vals:
        raise ValueError("negative-family values must be non-empty")
    return float(np.mean([value >= threshold for value in vals]))


def _calibrate_threshold(
    negative_families: Mapping[str, list[float]],
    *,
    alpha: float,
) -> tuple[float, dict[str, float]]:
    if not negative_families:
        raise ValueError("negative_families must be non-empty")
    all_values = [value for values in negative_families.values() for value in values]
    for threshold in _candidate_thresholds(all_values):
        rates = {
            family: _false_support_rate(values, threshold)
            for family, values in negative_families.items()
        }
        if max(rates.values()) <= alpha + 1e-12:
            return float(threshold), rates
    raise AssertionError("above-maximum threshold should always satisfy calibration")


def _truth_decision(scenario: str) -> str:
    if scenario == "target_only":
        return "T"
    if scenario in v3.NOISE_SCENARIOS:
        return "N"
    if scenario in v3.MIXED_TARGET_SCENARIOS:
        return "U"
    raise ValueError(f"unknown scenario: {scenario}")


def _false_certainty(decision: str, scenario: str) -> bool:
    if scenario == "target_only":
        return decision == "N"
    if scenario in v3.NOISE_SCENARIOS:
        return decision == "T"
    if scenario in v3.MIXED_TARGET_SCENARIOS:
        return decision in {"T", "N"}
    raise ValueError(scenario)


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unique = [row for row in rows if row["scenario"] in UNIQUE_SCENARIOS]
    mixed = [row for row in rows if row["scenario"] in MIXED_SCENARIOS]
    target_only = [row for row in rows if row["scenario"] == "target_only"]

    by_scenario: dict[str, Any] = {}
    for scenario in v3.SCENARIOS:
        subset = [row for row in rows if row["scenario"] == scenario]
        decisions = Counter(row["decision"] for row in subset)
        reasons = Counter(row["reason"] for row in subset)
        by_scenario[scenario] = {
            "n": len(subset),
            "T_rate": decisions["T"] / len(subset),
            "N_rate": decisions["N"] / len(subset),
            "U_rate": decisions["U"] / len(subset),
            "target_support_rate": float(np.mean([row["target_supported"] for row in subset])),
            "nuisance_support_rate": float(np.mean([row["nuisance_supported"] for row in subset])),
            "false_certainty_rate": float(np.mean([row["false_certainty"] for row in subset])),
            "u_overlap_reason_rate": reasons["target_nuisance_overlap"] / len(subset),
            "u_no_support_reason_rate": reasons["no_supported_evidence"] / len(subset),
        }

    target_false_support_by_family = {
        scenario: float(
            np.mean([row["target_supported"] for row in rows if row["scenario"] == scenario])
        )
        for scenario in v3.NOISE_SCENARIOS
    }

    return {
        "n": len(rows),
        "safe_unique_coverage": float(
            np.mean([row["decision"] == row["truth_decision"] for row in unique])
        ),
        "pooled_false_certainty_rate": float(np.mean([row["false_certainty"] for row in rows])),
        "overlap_abstention_rate": float(np.mean([row["decision"] == "U" for row in mixed])),
        "overlap_reason_rate": float(
            np.mean([row["reason"] == "target_nuisance_overlap" for row in mixed])
        ),
        "forced_unique_overlap_rate": float(np.mean([row["decision"] in {"T", "N"} for row in mixed])),
        "target_only_T_rate": float(np.mean([row["decision"] == "T" for row in target_only])),
        "target_false_support_by_nuisance_family": target_false_support_by_family,
        "max_target_false_support_rate": max(target_false_support_by_family.values()),
        "nuisance_false_support_rate_target_only": float(
            np.mean([row["nuisance_supported"] for row in target_only])
        ),
        "by_scenario": by_scenario,
    }


def _replicate_metric(rows: list[dict[str, Any]], rep: int, metric: str) -> float:
    subset = [row for row in rows if row["rep"] == rep]
    if metric == "safe_unique_coverage":
        unique = [row for row in subset if row["scenario"] in UNIQUE_SCENARIOS]
        return float(np.mean([row["decision"] == row["truth_decision"] for row in unique]))
    if metric == "pooled_false_certainty_rate":
        return float(np.mean([row["false_certainty"] for row in subset]))
    raise ValueError(metric)


def _paired_bootstrap_difference(
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
    heldout_reps: list[int],
    *,
    metric: str,
    n_bootstrap: int,
    seed: int,
) -> dict[str, float]:
    a = np.asarray([_replicate_metric(rows_a, rep, metric) for rep in heldout_reps], dtype=float)
    b = np.asarray([_replicate_metric(rows_b, rep, metric) for rep in heldout_reps], dtype=float)
    diffs = a - b
    rng = np.random.default_rng(seed)
    boot = np.empty(n_bootstrap, dtype=float)
    n = len(diffs)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        boot[i] = float(np.mean(diffs[idx]))
    return {
        "estimate": float(np.mean(diffs)),
        "ci95_low": float(np.quantile(boot, 0.025)),
        "ci95_high": float(np.quantile(boot, 0.975)),
    }


def evaluate_bridge(
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
        "schema": "pollipi-v3-tnoa-synthetic-bridge-v1",
        "protocol": "docs/V3_TNOA_SYNTHETIC_BRIDGE.md",
        "fresh_generation_note": (
            "Post-V3 bridge hypothesis evaluated on a fresh master seed; not preregistered before the original V3 result."
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
            "arms": list(ARMS),
            "scenarios": list(v3.SCENARIOS),
        },
        "calibration": calibration,
        "heldout_metrics": metrics,
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
            "Fresh controlled synthetic bridge only. Does not establish real-field performance, biological absence, "
            "physical nuisance identity, universal cross-domain benefit, or live-control readiness."
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

    result = evaluate_bridge(
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
