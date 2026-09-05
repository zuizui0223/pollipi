"""Post-primary robustness benchmark for degraded event-matched references.

This module keeps the primary synthetic worlds and frozen V1 classifier unchanged
while degrading only the target-free reference channel. Protocol:
``docs/LATENT_DISTURBANCE_V2_REFERENCE_ROBUSTNESS.md``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.schemas.states import (
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)
from pollipi_analysis.simulation.latent_disturbance_v2 import (
    DEFAULT_REPS,
    MASTER_SEED,
    MIXED_TARGET_SCENARIOS,
    NOISE_SCENARIOS,
    SCENARIOS,
    generate_world,
    project_reference,
)

ROBUSTNESS_CONDITIONS = (
    "gain_noise_reference",
    "shift2_reference",
    "partial75_reference",
    "no_reference",
)


def _shift_no_wrap(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Translate an array while filling newly exposed pixels with zeros."""
    out = np.zeros_like(arr)
    h, w = arr.shape
    y_src0 = max(0, -dy)
    y_src1 = min(h, h - dy) if dy >= 0 else h
    x_src0 = max(0, -dx)
    x_src1 = min(w, w - dx) if dx >= 0 else w
    y_dst0 = max(0, dy)
    x_dst0 = max(0, dx)
    height = y_src1 - y_src0
    width = x_src1 - x_src0
    if height > 0 and width > 0:
        out[y_dst0:y_dst0 + height, x_dst0:x_dst0 + width] = arr[y_src0:y_src1, x_src0:x_src1]
    return out


def degraded_reference(world, condition: str, seed: int) -> np.ndarray | None:
    """Return one frozen degraded target-free reference condition."""
    if condition == "no_reference":
        return None

    rng = np.random.default_rng(seed)
    bg = np.asarray(world.background, dtype=np.float32)
    correct_delta = np.asarray(world.correct_reference - bg, dtype=np.float32)
    corrupt_delta = np.asarray(world.corrupted_reference - bg, dtype=np.float32)

    if condition == "gain_noise_reference":
        gain = float(rng.uniform(0.70, 1.30))
        noise = rng.normal(0.0, 2.5, size=bg.shape).astype(np.float32)
        delta = gain * correct_delta + noise
    elif condition == "shift2_reference":
        choices = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3) if (dy, dx) != (0, 0)]
        dy, dx = choices[int(rng.integers(0, len(choices)))]
        noise = rng.normal(0.0, 1.5, size=bg.shape).astype(np.float32)
        delta = _shift_no_wrap(correct_delta, dy, dx) + noise
    elif condition == "partial75_reference":
        noise = rng.normal(0.0, 1.5, size=bg.shape).astype(np.float32)
        delta = 0.75 * correct_delta + 0.25 * corrupt_delta + noise
    else:
        raise ValueError(f"unknown robustness condition: {condition}")

    return np.clip(bg + delta, 0, 255).astype(np.float32)


def _is_local_candidate(state: str) -> bool:
    return state in (UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE)


def evaluate_reference_robustness(*, n_reps: int = DEFAULT_REPS, seed: int = MASTER_SEED) -> dict[str, Any]:
    if n_reps <= 0:
        raise ValueError("n_reps must be positive")

    counts: dict[str, dict[str, int]] = {
        condition: {scenario: 0 for scenario in SCENARIOS}
        for condition in ROBUSTNESS_CONDITIONS
    }
    alphas: dict[str, list[float]] = {condition: [] for condition in ROBUSTNESS_CONDITIONS}
    state_counts: dict[str, dict[str, dict[str, int]]] = {
        condition: {scenario: {} for scenario in SCENARIOS}
        for condition in ROBUSTNESS_CONDITIONS
    }

    for scenario_index, scenario in enumerate(SCENARIOS):
        for rep in range(n_reps):
            world_seed = seed + scenario_index * 100_000 + rep
            world = generate_world(scenario, world_seed)
            for condition_index, condition in enumerate(ROBUSTNESS_CONDITIONS):
                reference_seed = seed + 50_000_000 + scenario_index * 100_000 + rep * 100 + condition_index
                reference = degraded_reference(world, condition, reference_seed)
                frame, alpha = project_reference(world.primary, world.background, reference)
                decision = analyze(frame, world.background)
                state = decision.state
                state_counts[condition][scenario][state] = state_counts[condition][scenario].get(state, 0) + 1
                counts[condition][scenario] += int(_is_local_candidate(state))
                alphas[condition].append(alpha)

    metrics: dict[str, Any] = {}
    for condition in ROBUSTNESS_CONDITIONS:
        rates = {scenario: counts[condition][scenario] / n_reps for scenario in SCENARIOS}
        mixed_recall = float(np.mean([rates[s] for s in MIXED_TARGET_SCENARIOS]))
        target_only_recall = rates["target_only"]
        nuisance_fpr = float(np.mean([rates[s] for s in NOISE_SCENARIOS]))
        balanced = (mixed_recall + (1.0 - nuisance_fpr)) / 2.0
        alpha_arr = np.asarray(alphas[condition], dtype=np.float64)
        metrics[condition] = {
            "mixed_target_recall": mixed_recall,
            "target_only_recall": target_only_recall,
            "nuisance_false_event_rate": nuisance_fpr,
            "balanced_utility": balanced,
            "per_scenario_local_candidate_rate": rates,
            "state_counts": state_counts[condition],
            "alpha_mean": float(np.mean(alpha_arr)),
            "alpha_median": float(np.median(alpha_arr)),
            "alpha_min": float(np.min(alpha_arr)),
            "alpha_max": float(np.max(alpha_arr)),
        }

    none = metrics["no_reference"]
    gain = metrics["gain_noise_reference"]
    shift = metrics["shift2_reference"]
    partial = metrics["partial75_reference"]
    degraded = (gain, shift, partial)
    criteria = {
        "gain_noise_mixed_recall_gain_ge_0_10": gain["mixed_target_recall"] - none["mixed_target_recall"] >= 0.10,
        "shift2_mixed_recall_gain_ge_0_10": shift["mixed_target_recall"] - none["mixed_target_recall"] >= 0.10,
        "partial75_balanced_utility_gain_ge_0_08": partial["balanced_utility"] - none["balanced_utility"] >= 0.08,
        "all_degraded_nuisance_fpr_within_plus_0_05": all(
            x["nuisance_false_event_rate"] <= none["nuisance_false_event_rate"] + 0.05 + 1e-12
            for x in degraded
        ),
        "all_degraded_target_only_loss_le_0_05": all(
            none["target_only_recall"] - x["target_only_recall"] <= 0.05 + 1e-12
            for x in degraded
        ),
    }

    return {
        "schema": "pollipi-latent-disturbance-v2-reference-robustness-v1",
        "master_seed": seed,
        "n_reps_per_scenario": n_reps,
        "conditions": list(ROBUSTNESS_CONDITIONS),
        "metrics": metrics,
        "promotion_rule": {
            "criteria": criteria,
            "promoted_to_reference_robust_candidate": all(criteria.values()),
        },
        "claim_boundary": (
            "Post-primary simulation robustness only. Passing supports real fixed-interval shadow collection; "
            "it does not establish physical disturbance identity or live field readiness."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_reference_robustness(n_reps=args.n_reps, seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
