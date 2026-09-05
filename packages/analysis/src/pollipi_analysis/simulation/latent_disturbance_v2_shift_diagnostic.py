"""Diagnose whether the frozen V2.1 single-pair objective identifies injected shifts."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from pollipi_analysis.simulation.latent_disturbance_v2 import (
    DEFAULT_REPS,
    MASTER_SEED,
    SCENARIOS,
    generate_world,
)
from pollipi_analysis.simulation.latent_disturbance_v2_alignment import (
    MAX_SHIFT,
    TRIM_FRACTION,
    _fit_alpha,
    _trimmed_abs_mean,
)
from pollipi_analysis.simulation.latent_disturbance_v2_robustness import (
    _shift_no_wrap,
    degraded_reference,
)

DIAGNOSTIC_SCENARIOS = tuple(s for s in SCENARIOS if s != "target_only")


def injected_shift_from_seed(seed: int) -> tuple[int, int]:
    """Reproduce the frozen shift2 generator's first RNG draw."""
    rng = np.random.default_rng(seed)
    choices = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3) if (dy, dx) != (0, 0)]
    return choices[int(rng.integers(0, len(choices)))]


def rank_alignment_candidates(primary: np.ndarray, background: np.ndarray, reference: np.ndarray) -> list[dict[str, Any]]:
    dp = np.asarray(primary, dtype=np.float64) - np.asarray(background, dtype=np.float64)
    dr0 = np.asarray(reference, dtype=np.float64) - np.asarray(background, dtype=np.float64)
    rows: list[dict[str, Any]] = []
    for dy in range(-MAX_SHIFT, MAX_SHIFT + 1):
        for dx in range(-MAX_SHIFT, MAX_SHIFT + 1):
            shifted = _shift_no_wrap(dr0, dy, dx).astype(np.float64)
            alpha = _fit_alpha(dp, shifted)
            residual = dp - alpha * shifted
            loss = _trimmed_abs_mean(residual, TRIM_FRACTION)
            rows.append({"dy": dy, "dx": dx, "alpha": alpha, "loss": loss})
    rows.sort(key=lambda r: (r["loss"], abs(r["dy"]) + abs(r["dx"]), r["dy"], r["dx"]))
    return rows


def _summary(records: list[dict[str, Any]]) -> dict[str, float]:
    if not records:
        return {
            "n": 0,
            "exact_rate": 0.0,
            "within_manhattan_1_rate": 0.0,
            "mean_manhattan_error": 0.0,
            "median_manhattan_error": 0.0,
            "mean_loss_margin": 0.0,
            "median_loss_margin": 0.0,
        }
    errors = np.asarray([r["manhattan_error"] for r in records], dtype=np.float64)
    margins = np.asarray([r["loss_margin"] for r in records], dtype=np.float64)
    return {
        "n": len(records),
        "exact_rate": float(np.mean(errors == 0)),
        "within_manhattan_1_rate": float(np.mean(errors <= 1)),
        "mean_manhattan_error": float(np.mean(errors)),
        "median_manhattan_error": float(np.median(errors)),
        "mean_loss_margin": float(np.mean(margins)),
        "median_loss_margin": float(np.median(margins)),
    }


def evaluate_shift_identifiability(*, n_reps: int = DEFAULT_REPS, seed: int = MASTER_SEED) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    selected_shift_counts: dict[str, int] = defaultdict(int)

    for scenario_index, scenario in enumerate(SCENARIOS):
        if scenario == "target_only":
            continue
        for rep in range(n_reps):
            world_seed = seed + scenario_index * 100_000 + rep
            world = generate_world(scenario, world_seed)
            ref_seed = seed + 50_000_000 + scenario_index * 100_000 + rep * 100 + 1
            injected = injected_shift_from_seed(ref_seed)
            expected = (-injected[0], -injected[1])
            reference = degraded_reference(world, "shift2_reference", ref_seed)
            assert reference is not None
            ranked = rank_alignment_candidates(world.primary, world.background, reference)
            best, second = ranked[0], ranked[1]
            selected = (int(best["dy"]), int(best["dx"]))
            error = abs(selected[0] - expected[0]) + abs(selected[1] - expected[1])
            margin = float(second["loss"] - best["loss"])
            selected_shift_counts[f"{selected[0]},{selected[1]}"] += 1
            records.append({
                "scenario": scenario,
                "nuisance": world.nuisance,
                "target_bearing": scenario.startswith("target_plus_"),
                "injected_shift": list(injected),
                "expected_inverse_shift": list(expected),
                "selected_shift": list(selected),
                "manhattan_error": int(error),
                "best_loss": float(best["loss"]),
                "second_loss": float(second["loss"]),
                "loss_margin": margin,
            })

    by_nuisance: dict[str, Any] = {}
    for nuisance in ("wind", "shadow", "shake", "local_sway"):
        by_nuisance[nuisance] = _summary([r for r in records if r["nuisance"] == nuisance])
    by_target_status = {
        "target_bearing": _summary([r for r in records if r["target_bearing"]]),
        "nuisance_only": _summary([r for r in records if not r["target_bearing"]]),
    }

    return {
        "schema": "pollipi-latent-disturbance-v2-shift-identifiability-v1",
        "master_seed": seed,
        "n_reps_per_scenario": n_reps,
        "scenarios": list(DIAGNOSTIC_SCENARIOS),
        "overall": _summary(records),
        "by_nuisance": by_nuisance,
        "by_target_status": by_target_status,
        "selected_shift_counts": dict(sorted(selected_shift_counts.items())),
        "distinct_selected_shift_count": len(selected_shift_counts),
        "interpretation_rule": (
            "Low exact recovery together with small best-vs-second loss margins indicates weak single-pair shift "
            "identifiability and motivates multi-frame/low-rank nuisance representations rather than further "
            "single-pair threshold tuning."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_shift_identifiability(n_reps=args.n_reps, seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
