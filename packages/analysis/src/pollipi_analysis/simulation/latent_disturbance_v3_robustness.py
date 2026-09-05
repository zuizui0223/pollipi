"""Secondary V3 robustness: imperfect temporal coupling, no tuning.

Protocol: docs/LATENT_DISTURBANCE_V3_TEMPORAL_ROBUSTNESS.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from pollipi_analysis.simulation.latent_disturbance_v3_temporal_subspace import (
    BROAD_NOISE_SCENARIOS,
    DEFAULT_REPS,
    MASTER_SEED,
    MIXED_TARGET_SCENARIOS,
    NOISE_SCENARIOS,
    SCENARIOS,
    T,
    TARGET_SCENARIOS,
    _evaluate_sequence,
    generate_temporal_world,
    temporal_subspace_project,
)

CONDITIONS = (
    "matched_temporal_reference",
    "lag1_reference",
    "partial75_reference",
    "no_reference",
)


def _lag1_reference(world) -> np.ndarray:
    delta = np.asarray(world.reference_frames, dtype=np.float32) - world.reference_background[None, :, :]
    lagged = np.concatenate([delta[:1], delta[:-1]], axis=0)
    return np.clip(world.reference_background[None, :, :] + lagged, 0, 255).astype(np.float32)


def _partial75_reference(world, seed: int) -> np.ndarray:
    delta = np.asarray(world.reference_frames, dtype=np.float32) - world.reference_background[None, :, :]
    rng = np.random.default_rng(seed)
    perm = rng.permutation(T)
    if np.array_equal(perm, np.arange(T)):
        perm = np.roll(perm, 1)
    mixed = 0.75 * delta + 0.25 * delta[perm]
    return np.clip(world.reference_background[None, :, :] + mixed, 0, 255).astype(np.float32)


def _aggregate(records: dict[str, dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for condition in CONDITIONS:
        per_scenario: dict[str, Any] = {}
        for scenario in SCENARIOS:
            rs = records[condition][scenario]
            recalls = [r["target_frame_recall"] for r in rs if r["target_frame_recall"] is not None]
            episodes = [bool(r["target_episode_detected"]) for r in rs if r["target_episode_detected"] is not None]
            per_scenario[scenario] = {
                "target_frame_recall": float(np.mean(recalls)) if recalls else None,
                "all_frame_local_rate": float(np.mean([r["all_frame_local_rate"] for r in rs])),
                "target_episode_recall": float(np.mean(episodes)) if episodes else None,
                "two_consecutive_local_rate": float(np.mean([r["two_consecutive_local"] for r in rs])),
            }
        mixed = float(np.mean([per_scenario[s]["target_frame_recall"] for s in MIXED_TARGET_SCENARIOS]))
        nuisance = float(np.mean([per_scenario[s]["all_frame_local_rate"] for s in NOISE_SCENARIOS]))
        metrics[condition] = {
            "mixed_target_frame_recall": mixed,
            "target_only_frame_recall": float(per_scenario["target_only"]["target_frame_recall"]),
            "nuisance_false_frame_rate": nuisance,
            "local_sway_false_frame_rate": float(per_scenario["local_sway_only"]["all_frame_local_rate"]),
            "broad_nuisance_false_frame_rate": float(np.mean([per_scenario[s]["all_frame_local_rate"] for s in BROAD_NOISE_SCENARIOS])),
            "target_episode_recall": float(np.mean([per_scenario[s]["target_episode_recall"] for s in TARGET_SCENARIOS])),
            "nuisance_false_episode_rate": float(np.mean([per_scenario[s]["two_consecutive_local_rate"] for s in NOISE_SCENARIOS])),
            "balanced_utility": (mixed + 1.0 - nuisance) / 2.0,
            "per_scenario": per_scenario,
        }
    return metrics


def evaluate_v3_robustness(*, n_reps: int = DEFAULT_REPS, seed: int = MASTER_SEED) -> dict[str, Any]:
    records = {c: {s: [] for s in SCENARIOS} for c in CONDITIONS}
    for si, scenario in enumerate(SCENARIOS):
        for rep in range(n_reps):
            world_seed = seed + si * 100_000 + rep
            world = generate_temporal_world(scenario, world_seed)
            lagged_ref = _lag1_reference(world)
            partial_ref = _partial75_reference(world, seed + 70_000_000 + si * 100_000 + rep)

            matched, _ = temporal_subspace_project(
                world.primary_frames, world.primary_background,
                world.reference_frames, world.reference_background,
            )
            lag1, _ = temporal_subspace_project(
                world.primary_frames, world.primary_background,
                lagged_ref, world.reference_background,
            )
            partial75, _ = temporal_subspace_project(
                world.primary_frames, world.primary_background,
                partial_ref, world.reference_background,
            )
            frames_by_condition = {
                "matched_temporal_reference": matched,
                "lag1_reference": lag1,
                "partial75_reference": partial75,
                "no_reference": world.primary_frames,
            }
            for condition, frames in frames_by_condition.items():
                records[condition][scenario].append(_evaluate_sequence(frames, world))

    metrics = _aggregate(records)
    none = metrics["no_reference"]
    lag = metrics["lag1_reference"]
    partial = metrics["partial75_reference"]
    criteria = {
        "lag1_utility_gain_vs_none_ge_0_08": lag["balanced_utility"] - none["balanced_utility"] >= 0.08,
        "lag1_nuisance_fpr_reduction_vs_none_ge_0_08": none["nuisance_false_frame_rate"] - lag["nuisance_false_frame_rate"] >= 0.08,
        "lag1_target_only_loss_le_0_06": none["target_only_frame_recall"] - lag["target_only_frame_recall"] <= 0.06 + 1e-12,
        "lag1_local_sway_fpr_reduction_vs_none_ge_0_25": none["local_sway_false_frame_rate"] - lag["local_sway_false_frame_rate"] >= 0.25,
        "lag1_broad_fpr_within_none_plus_0_05": lag["broad_nuisance_false_frame_rate"] <= none["broad_nuisance_false_frame_rate"] + 0.05 + 1e-12,
        "partial75_utility_gain_vs_none_ge_0_10": partial["balanced_utility"] - none["balanced_utility"] >= 0.10,
        "partial75_nuisance_fpr_reduction_vs_none_ge_0_10": none["nuisance_false_frame_rate"] - partial["nuisance_false_frame_rate"] >= 0.10,
        "partial75_target_only_loss_le_0_06": none["target_only_frame_recall"] - partial["target_only_frame_recall"] <= 0.06 + 1e-12,
        "partial75_local_sway_fpr_reduction_vs_none_ge_0_25": none["local_sway_false_frame_rate"] - partial["local_sway_false_frame_rate"] >= 0.25,
        "partial75_broad_fpr_within_none_plus_0_05": partial["broad_nuisance_false_frame_rate"] <= none["broad_nuisance_false_frame_rate"] + 0.05 + 1e-12,
    }
    return {
        "schema": "pollipi-latent-disturbance-v3-temporal-robustness-v1",
        "master_seed": seed,
        "n_reps_per_scenario": n_reps,
        "conditions": list(CONDITIONS),
        "metrics": metrics,
        "promotion_rule": {
            "criteria": criteria,
            "promoted_to_temporally_robust_simulation_candidate": all(criteria.values()),
        },
        "claim_boundary": "Simulation-only stress test of one-frame lag and 75% temporal coupling; no arbitrary drift or field-performance claim.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n-reps", type=int, default=DEFAULT_REPS)
    p.add_argument("--seed", type=int, default=MASTER_SEED)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = evaluate_v3_robustness(n_reps=args.n_reps, seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
