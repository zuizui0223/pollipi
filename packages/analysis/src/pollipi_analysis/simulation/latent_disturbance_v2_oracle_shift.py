"""Oracle-shift diagnostic for localizing V2 spatial-reference failure.

The oracle arm uses injected simulation metadata and is never a deployable method.
Protocol: ``docs/LATENT_DISTURBANCE_V2_ORACLE_SHIFT_DIAGNOSTIC.md``.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.schemas.states import STRONG_VISITATION_CANDIDATE, UNCERTAIN_LOCAL_ACTIVITY
from pollipi_analysis.simulation.latent_disturbance_v2 import (
    DEFAULT_REPS,
    MASTER_SEED,
    MIXED_TARGET_SCENARIOS,
    NOISE_SCENARIOS,
    SCENARIOS,
    generate_world,
    project_reference,
)
from pollipi_analysis.simulation.latent_disturbance_v2_alignment import align_and_project
from pollipi_analysis.simulation.latent_disturbance_v2_robustness import _shift_no_wrap, degraded_reference
from pollipi_analysis.simulation.latent_disturbance_v2_shift_diagnostic import injected_shift_from_seed

CONDITIONS = (
    "exact_reference",
    "oracle_shift_reference",
    "estimated_shift_v2_1",
    "shift2_unaligned",
    "no_reference",
)
BORDER_WIDTH = 4


def _is_local_candidate(state: str) -> bool:
    return state in (UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE)


def oracle_restore_reference(
    background: np.ndarray,
    shifted_reference: np.ndarray,
    injected_shift: tuple[int, int],
) -> np.ndarray:
    """Apply the known inverse injected translation to a degraded reference."""
    delta = np.asarray(shifted_reference, dtype=np.float32) - np.asarray(background, dtype=np.float32)
    restored = _shift_no_wrap(delta, -injected_shift[0], -injected_shift[1])
    return np.clip(np.asarray(background, dtype=np.float32) + restored, 0, 255).astype(np.float32)


def border_excess(frame: np.ndarray, background: np.ndarray, border_width: int = BORDER_WIDTH) -> float:
    """Residual-energy concentration in the image border relative to border area."""
    residual = np.abs(np.asarray(frame, dtype=np.float64) - np.asarray(background, dtype=np.float64))
    h, w = residual.shape
    bw = min(border_width, h // 2, w // 2)
    mask = np.zeros((h, w), dtype=bool)
    mask[:bw, :] = True
    mask[-bw:, :] = True
    mask[:, :bw] = True
    mask[:, -bw:] = True
    total = float(np.sum(residual))
    if total <= 1e-12:
        return 0.0
    border_fraction = float(np.sum(residual[mask]) / total)
    area_fraction = float(np.mean(mask))
    return border_fraction / area_fraction if area_fraction > 0 else 0.0


def evaluate_oracle_shift(*, n_reps: int = DEFAULT_REPS, seed: int = MASTER_SEED) -> dict[str, Any]:
    if n_reps <= 0:
        raise ValueError("n_reps must be positive")

    counts = {condition: {scenario: 0 for scenario in SCENARIOS} for condition in CONDITIONS}
    state_counts = {condition: {scenario: {} for scenario in SCENARIOS} for condition in CONDITIONS}
    border_values: dict[str, dict[str, list[float]]] = {
        condition: {scenario: [] for scenario in NOISE_SCENARIOS}
        for condition in CONDITIONS
    }

    for scenario_index, scenario in enumerate(SCENARIOS):
        for rep in range(n_reps):
            world_seed = seed + scenario_index * 100_000 + rep
            world = generate_world(scenario, world_seed)
            ref_seed = seed + 50_000_000 + scenario_index * 100_000 + rep * 100 + 1
            shifted_reference = degraded_reference(world, "shift2_reference", ref_seed)
            assert shifted_reference is not None
            injected = injected_shift_from_seed(ref_seed)

            exact_frame, _ = project_reference(world.primary, world.background, world.correct_reference)
            oracle_ref = oracle_restore_reference(world.background, shifted_reference, injected)
            oracle_frame, _ = project_reference(world.primary, world.background, oracle_ref)
            estimated_frame, _, _, _ = align_and_project(world.primary, world.background, shifted_reference)
            unaligned_frame, _ = project_reference(world.primary, world.background, shifted_reference)

            frames = {
                "exact_reference": exact_frame,
                "oracle_shift_reference": oracle_frame,
                "estimated_shift_v2_1": estimated_frame,
                "shift2_unaligned": unaligned_frame,
                "no_reference": world.primary,
            }

            for condition, frame in frames.items():
                decision = analyze(frame, world.background)
                state = decision.state
                state_counts[condition][scenario][state] = state_counts[condition][scenario].get(state, 0) + 1
                counts[condition][scenario] += int(_is_local_candidate(state))
                if scenario in NOISE_SCENARIOS:
                    border_values[condition][scenario].append(border_excess(frame, world.background))

    metrics: dict[str, Any] = {}
    for condition in CONDITIONS:
        rates = {scenario: counts[condition][scenario] / n_reps for scenario in SCENARIOS}
        mixed_recall = float(np.mean([rates[s] for s in MIXED_TARGET_SCENARIOS]))
        nuisance_fpr = float(np.mean([rates[s] for s in NOISE_SCENARIOS]))
        per_nuisance_border = {
            scenario: {
                "mean": float(np.mean(border_values[condition][scenario])),
                "median": float(np.median(border_values[condition][scenario])),
            }
            for scenario in NOISE_SCENARIOS
        }
        all_border = [x for scenario in NOISE_SCENARIOS for x in border_values[condition][scenario]]
        metrics[condition] = {
            "mixed_target_recall": mixed_recall,
            "target_only_recall": rates["target_only"],
            "nuisance_false_event_rate": nuisance_fpr,
            "balanced_utility": (mixed_recall + (1.0 - nuisance_fpr)) / 2.0,
            "per_scenario_local_candidate_rate": rates,
            "state_counts": state_counts[condition],
            "nuisance_border_excess": {
                "overall_mean": float(np.mean(all_border)),
                "overall_median": float(np.median(all_border)),
                "by_scenario": per_nuisance_border,
            },
        }

    return {
        "schema": "pollipi-latent-disturbance-v2-oracle-shift-diagnostic-v1",
        "master_seed": seed,
        "n_reps_per_scenario": n_reps,
        "border_width_px": BORDER_WIDTH,
        "conditions": list(CONDITIONS),
        "metrics": metrics,
        "interpretation_rules": {
            "alignment_failure": "oracle shift clean but estimated shift noisy",
            "post_alignment_failure": "oracle and estimated shift both noisy",
            "boundary_information_failure": "exact reference clean, oracle shift noisy, and oracle border excess elevated",
        },
        "claim_boundary": "Diagnostic only; oracle injected-shift metadata is unavailable in deployment.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_oracle_shift(n_reps=args.n_reps, seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
