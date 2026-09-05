"""V2.1 label-free alignment before reference-guided nuisance projection."""
from __future__ import annotations

import argparse
import json
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
from pollipi_analysis.simulation.latent_disturbance_v2_robustness import (
    _shift_no_wrap,
    degraded_reference,
)

MAX_SHIFT = 2
TRIM_FRACTION = 0.10
CONDITIONS = ("shift2_aligned_v2_1", "shift2_unaligned", "no_reference")


def _fit_alpha(dp: np.ndarray, dr: np.ndarray) -> float:
    denom = float(np.vdot(dr, dr).real)
    if denom <= 1e-12:
        return 0.0
    return float(np.clip(float(np.vdot(dp, dr).real) / denom, 0.0, 1.5))


def _trimmed_abs_mean(residual: np.ndarray, trim_fraction: float = TRIM_FRACTION) -> float:
    values = np.abs(np.asarray(residual, dtype=np.float64)).ravel()
    if values.size == 0:
        return 0.0
    keep = max(1, int(np.floor(values.size * (1.0 - trim_fraction))))
    # Partition rather than sort the full frame. The largest residual pixels are
    # excluded so a compact target does not determine reference alignment.
    smallest = np.partition(values, keep - 1)[:keep]
    return float(np.mean(smallest))


def align_and_project(
    primary: np.ndarray,
    background: np.ndarray,
    reference: np.ndarray,
    *,
    max_shift: int = MAX_SHIFT,
    trim_fraction: float = TRIM_FRACTION,
) -> tuple[np.ndarray, float, tuple[int, int], float]:
    """Search a small label-free translation, then perform V2 projection.

    Returns ``(corrected_frame, alpha, (dy, dx), alignment_loss)``.
    """
    dp = np.asarray(primary, dtype=np.float64) - np.asarray(background, dtype=np.float64)
    dr0 = np.asarray(reference, dtype=np.float64) - np.asarray(background, dtype=np.float64)
    best: tuple[float, float, int, int, np.ndarray] | None = None
    for dy in range(-max_shift, max_shift + 1):
        for dx in range(-max_shift, max_shift + 1):
            shifted = _shift_no_wrap(dr0, dy, dx).astype(np.float64)
            alpha = _fit_alpha(dp, shifted)
            residual = dp - alpha * shifted
            loss = _trimmed_abs_mean(residual, trim_fraction)
            candidate = (loss, alpha, dy, dx, residual)
            if best is None or (loss, abs(dy) + abs(dx), dy, dx) < (
                best[0], abs(best[2]) + abs(best[3]), best[2], best[3]
            ):
                best = candidate
    assert best is not None
    loss, alpha, dy, dx, residual = best
    corrected = np.asarray(background, dtype=np.float64) + residual
    return np.clip(corrected, 0, 255).astype(np.float32), alpha, (dy, dx), loss


def _is_local_candidate(state: str) -> bool:
    return state in (UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE)


def evaluate_alignment(*, n_reps: int = DEFAULT_REPS, seed: int = MASTER_SEED) -> dict[str, Any]:
    if n_reps <= 0:
        raise ValueError("n_reps must be positive")

    counts = {condition: {scenario: 0 for scenario in SCENARIOS} for condition in CONDITIONS}
    state_counts = {condition: {scenario: {} for scenario in SCENARIOS} for condition in CONDITIONS}
    aligned_shifts: dict[str, int] = {}
    aligned_alphas: list[float] = []
    aligned_losses: list[float] = []

    for scenario_index, scenario in enumerate(SCENARIOS):
        for rep in range(n_reps):
            world_seed = seed + scenario_index * 100_000 + rep
            world = generate_world(scenario, world_seed)
            ref_seed = seed + 50_000_000 + scenario_index * 100_000 + rep * 100 + 1
            shifted_reference = degraded_reference(world, "shift2_reference", ref_seed)
            assert shifted_reference is not None

            unaligned_frame, _ = project_reference(world.primary, world.background, shifted_reference)
            aligned_frame, alpha, shift, loss = align_and_project(
                world.primary, world.background, shifted_reference
            )
            frames = {
                "shift2_aligned_v2_1": aligned_frame,
                "shift2_unaligned": unaligned_frame,
                "no_reference": world.primary,
            }
            key = f"{shift[0]},{shift[1]}"
            aligned_shifts[key] = aligned_shifts.get(key, 0) + 1
            aligned_alphas.append(alpha)
            aligned_losses.append(loss)

            for condition, frame in frames.items():
                decision = analyze(frame, world.background)
                state = decision.state
                state_counts[condition][scenario][state] = state_counts[condition][scenario].get(state, 0) + 1
                counts[condition][scenario] += int(_is_local_candidate(state))

    metrics: dict[str, Any] = {}
    for condition in CONDITIONS:
        rates = {scenario: counts[condition][scenario] / n_reps for scenario in SCENARIOS}
        mixed_recall = float(np.mean([rates[s] for s in MIXED_TARGET_SCENARIOS]))
        target_only_recall = rates["target_only"]
        nuisance_fpr = float(np.mean([rates[s] for s in NOISE_SCENARIOS]))
        metrics[condition] = {
            "mixed_target_recall": mixed_recall,
            "target_only_recall": target_only_recall,
            "nuisance_false_event_rate": nuisance_fpr,
            "balanced_utility": (mixed_recall + (1.0 - nuisance_fpr)) / 2.0,
            "per_scenario_local_candidate_rate": rates,
            "state_counts": state_counts[condition],
        }

    aligned = metrics["shift2_aligned_v2_1"]
    unaligned = metrics["shift2_unaligned"]
    none = metrics["no_reference"]
    criteria = {
        "aligned_mixed_recall_gain_vs_none_ge_0_10": aligned["mixed_target_recall"] - none["mixed_target_recall"] >= 0.10,
        "aligned_nuisance_fpr_within_none_plus_0_05": aligned["nuisance_false_event_rate"] <= none["nuisance_false_event_rate"] + 0.05 + 1e-12,
        "aligned_balanced_utility_gain_vs_unaligned_ge_0_08": aligned["balanced_utility"] - unaligned["balanced_utility"] >= 0.08,
        "aligned_target_only_loss_le_0_05": none["target_only_recall"] - aligned["target_only_recall"] <= 0.05 + 1e-12,
        "multiple_alignment_shifts_selected": len(aligned_shifts) >= 2,
    }

    alpha_arr = np.asarray(aligned_alphas, dtype=np.float64)
    loss_arr = np.asarray(aligned_losses, dtype=np.float64)
    return {
        "schema": "pollipi-latent-disturbance-v2-1-alignment-v1",
        "master_seed": seed,
        "n_reps_per_scenario": n_reps,
        "max_shift_px": MAX_SHIFT,
        "trim_fraction": TRIM_FRACTION,
        "metrics": metrics,
        "alignment": {
            "selected_shift_counts": dict(sorted(aligned_shifts.items())),
            "distinct_shift_count": len(aligned_shifts),
            "alpha_mean": float(np.mean(alpha_arr)),
            "alpha_median": float(np.median(alpha_arr)),
            "loss_mean": float(np.mean(loss_arr)),
            "loss_median": float(np.median(loss_arr)),
        },
        "promotion_rule": {
            "criteria": criteria,
            "promoted_to_simulation_robust_field_shadow_candidate": all(criteria.values()),
        },
        "claim_boundary": (
            "Simulation-only post-failure revision. Passing authorizes only real fixed-interval shadow collection "
            "with target-free reference evidence; live adaptation remains disabled."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_alignment(n_reps=args.n_reps, seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
