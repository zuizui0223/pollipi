"""Simulation-only V2 benchmark for reference-guided latent nuisance projection.

The downstream classifier is intentionally the existing V1 ``pipeline.analyze``.
V2 only changes the observation representation before that fixed classifier.
See ``docs/LATENT_DISTURBANCE_V2_BENCHMARK.md`` for the frozen protocol.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.schemas.states import (
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)

MASTER_SEED = 20260905
DEFAULT_REPS = 64
SIZE = (192, 256)
REFERENCE_CONDITIONS = ("correct_reference", "corrupted_reference", "no_reference")
TARGET_SCENARIOS = (
    "target_only",
    "target_plus_wind",
    "target_plus_shadow",
    "target_plus_shake",
    "target_plus_local_sway",
)
MIXED_TARGET_SCENARIOS = TARGET_SCENARIOS[1:]
NOISE_SCENARIOS = ("wind_only", "shadow_only", "shake_only", "local_sway_only")
SCENARIOS = TARGET_SCENARIOS + NOISE_SCENARIOS


@dataclass(frozen=True)
class LatentWorld:
    scenario: str
    background: np.ndarray
    primary: np.ndarray
    correct_reference: np.ndarray
    corrupted_reference: np.ndarray
    has_target: bool
    nuisance: str | None


def _background(rng: np.random.Generator, size: tuple[int, int] = SIZE) -> np.ndarray:
    h, w = size
    bg = np.full((h, w), 96.0, dtype=np.float32)
    bg += np.linspace(-22, 22, w, dtype=np.float32)[None, :]
    bg += np.linspace(-8, 8, h, dtype=np.float32)[:, None]
    bg += rng.normal(0, 1.5, size=(h, w)).astype(np.float32)
    return bg


def _disc_layer(shape: tuple[int, int], cy: int, cx: int, radius: int, amplitude: float) -> np.ndarray:
    yy, xx = np.ogrid[: shape[0], : shape[1]]
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
    out = np.zeros(shape, dtype=np.float32)
    out[mask] = amplitude
    return out


def _target_layer(rng: np.random.Generator, shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    cy = int(h * 0.50 + rng.integers(-5, 6))
    cx = int(w * 0.44 + rng.integers(-7, 8))
    radius = int(rng.integers(6, 9))
    amplitude = float(rng.uniform(66.0, 82.0))
    return _disc_layer(shape, cy, cx, radius, amplitude)


def _wind_layer(rng: np.random.Generator, shape: tuple[int, int], *, corrupt: bool = False) -> np.ndarray:
    h, w = shape
    x = np.linspace(0, 8, w, dtype=np.float32)
    phase = float(rng.uniform(-0.35, 0.35))
    if corrupt:
        phase += float(rng.uniform(1.2, 2.4))
    amp = float(rng.uniform(28.0, 36.0))
    stripes = (np.sin(x + phase)[None, :] > 0).astype(np.float32)
    layer = amp * stripes
    return np.broadcast_to(layer, (h, w)).copy()


def _shadow_layer(rng: np.random.Generator, shape: tuple[int, int], *, corrupt: bool = False) -> np.ndarray:
    h, w = shape
    width = int(w * rng.uniform(0.50, 0.68))
    start = int(w * rng.uniform(0.12, 0.28))
    if corrupt:
        start = int(w * rng.uniform(0.48, 0.72))
    end = min(w, start + width)
    amp = float(rng.uniform(-31.0, -24.0))
    out = np.zeros((h, w), dtype=np.float32)
    out[:, start:end] = amp
    return out


def _shake_layer(
    rng: np.random.Generator,
    background: np.ndarray,
    *,
    corrupt: bool = False,
) -> np.ndarray:
    dx = int(rng.choice([-6, -5, 5, 6]))
    dy = int(rng.choice([-2, -1, 1, 2]))
    if corrupt:
        dx = -dx
        dy = int(rng.choice([-3, 3]))
    shifted = np.roll(np.roll(background, shift=dy, axis=0), shift=dx, axis=1)
    return shifted.astype(np.float32) - background


def _local_sway_layer(
    rng: np.random.Generator,
    shape: tuple[int, int],
    *,
    corrupt: bool = False,
) -> np.ndarray:
    h, w = shape
    cy = int(h * 0.31 + rng.integers(-5, 6))
    cx = int(w * 0.72 + rng.integers(-6, 7))
    if corrupt:
        cy = int(h * 0.70 + rng.integers(-5, 6))
        cx = int(w * 0.76 + rng.integers(-6, 7))
    radius = int(rng.integers(8, 11))
    amp = float(rng.uniform(28.0, 38.0))
    return _disc_layer(shape, cy, cx, radius, amp)


def _nuisance_layers(
    nuisance: str | None,
    rng: np.random.Generator,
    corrupt_rng: np.random.Generator,
    background: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    shape = background.shape
    zero = np.zeros(shape, dtype=np.float32)
    if nuisance is None:
        return zero, zero.copy()
    if nuisance == "wind":
        return _wind_layer(rng, shape), _wind_layer(corrupt_rng, shape, corrupt=True)
    if nuisance == "shadow":
        return _shadow_layer(rng, shape), _shadow_layer(corrupt_rng, shape, corrupt=True)
    if nuisance == "shake":
        return _shake_layer(rng, background), _shake_layer(corrupt_rng, background, corrupt=True)
    if nuisance == "local_sway":
        return _local_sway_layer(rng, shape), _local_sway_layer(corrupt_rng, shape, corrupt=True)
    raise ValueError(f"unknown nuisance: {nuisance}")


def _scenario_parts(scenario: str) -> tuple[bool, str | None]:
    mapping = {
        "target_only": (True, None),
        "target_plus_wind": (True, "wind"),
        "target_plus_shadow": (True, "shadow"),
        "target_plus_shake": (True, "shake"),
        "target_plus_local_sway": (True, "local_sway"),
        "wind_only": (False, "wind"),
        "shadow_only": (False, "shadow"),
        "shake_only": (False, "shake"),
        "local_sway_only": (False, "local_sway"),
    }
    try:
        return mapping[scenario]
    except KeyError as exc:
        raise ValueError(f"unknown scenario: {scenario}") from exc


def generate_world(scenario: str, seed: int) -> LatentWorld:
    """Generate one paired primary/reference latent world.

    The primary and correct reference share the exact nuisance realization. Only
    the primary contains target signal. Corrupted reference retains nuisance type
    but breaks realization-level coupling.
    """
    has_target, nuisance = _scenario_parts(scenario)
    rng = np.random.default_rng(seed)
    corrupt_rng = np.random.default_rng(seed + 10_000_019)
    bg = _background(rng)
    target = _target_layer(rng, bg.shape) if has_target else np.zeros_like(bg)
    nuisance_layer, corrupted_layer = _nuisance_layers(nuisance, rng, corrupt_rng, bg)
    primary = np.clip(bg + nuisance_layer + target, 0, 255).astype(np.float32)
    correct_reference = np.clip(bg + nuisance_layer, 0, 255).astype(np.float32)
    corrupted_reference = np.clip(bg + corrupted_layer, 0, 255).astype(np.float32)
    return LatentWorld(
        scenario=scenario,
        background=bg,
        primary=primary,
        correct_reference=correct_reference,
        corrupted_reference=corrupted_reference,
        has_target=has_target,
        nuisance=nuisance,
    )


def project_reference(primary: np.ndarray, background: np.ndarray, reference: np.ndarray | None) -> tuple[np.ndarray, float]:
    """Remove the one-dimensional nuisance component carried by ``reference``."""
    if reference is None:
        return np.asarray(primary, dtype=np.float32).copy(), 0.0
    dp = np.asarray(primary, dtype=np.float64) - np.asarray(background, dtype=np.float64)
    dr = np.asarray(reference, dtype=np.float64) - np.asarray(background, dtype=np.float64)
    denom = float(np.vdot(dr, dr).real)
    if denom <= 1e-12:
        return np.asarray(primary, dtype=np.float32).copy(), 0.0
    alpha = float(np.clip(float(np.vdot(dp, dr).real) / denom, 0.0, 1.5))
    residual = dp - alpha * dr
    corrected = np.asarray(background, dtype=np.float64) + residual
    return np.clip(corrected, 0, 255).astype(np.float32), alpha


def _is_local_candidate(state: str) -> bool:
    return state in (UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE)


def evaluate(*, n_reps: int = DEFAULT_REPS, seed: int = MASTER_SEED) -> dict[str, Any]:
    if n_reps <= 0:
        raise ValueError("n_reps must be positive")

    counts: dict[str, dict[str, int]] = {
        condition: {scenario: 0 for scenario in SCENARIOS}
        for condition in REFERENCE_CONDITIONS
    }
    alphas: dict[str, list[float]] = {condition: [] for condition in REFERENCE_CONDITIONS}
    state_counts: dict[str, dict[str, dict[str, int]]] = {
        condition: {scenario: {} for scenario in SCENARIOS}
        for condition in REFERENCE_CONDITIONS
    }

    for scenario_index, scenario in enumerate(SCENARIOS):
        for rep in range(n_reps):
            world_seed = seed + scenario_index * 100_000 + rep
            world = generate_world(scenario, world_seed)
            refs = {
                "correct_reference": world.correct_reference,
                "corrupted_reference": world.corrupted_reference,
                "no_reference": None,
            }
            for condition, reference in refs.items():
                frame, alpha = project_reference(world.primary, world.background, reference)
                decision = analyze(frame, world.background)
                state = decision.state
                state_counts[condition][scenario][state] = state_counts[condition][scenario].get(state, 0) + 1
                counts[condition][scenario] += int(_is_local_candidate(state))
                alphas[condition].append(alpha)

    metrics: dict[str, Any] = {}
    for condition in REFERENCE_CONDITIONS:
        per_scenario = {
            scenario: counts[condition][scenario] / n_reps
            for scenario in SCENARIOS
        }
        mixed_recall = float(np.mean([per_scenario[s] for s in MIXED_TARGET_SCENARIOS]))
        target_only_recall = per_scenario["target_only"]
        nuisance_fpr = float(np.mean([per_scenario[s] for s in NOISE_SCENARIOS]))
        balanced = (mixed_recall + (1.0 - nuisance_fpr)) / 2.0
        alpha_arr = np.asarray(alphas[condition], dtype=np.float64)
        metrics[condition] = {
            "mixed_target_recall": mixed_recall,
            "target_only_recall": target_only_recall,
            "nuisance_false_event_rate": nuisance_fpr,
            "balanced_utility": balanced,
            "per_scenario_local_candidate_rate": per_scenario,
            "state_counts": state_counts[condition],
            "alpha_mean": float(np.mean(alpha_arr)),
            "alpha_median": float(np.median(alpha_arr)),
            "alpha_min": float(np.min(alpha_arr)),
            "alpha_max": float(np.max(alpha_arr)),
        }

    correct = metrics["correct_reference"]
    corrupt = metrics["corrupted_reference"]
    none = metrics["no_reference"]
    criteria = {
        "mixed_target_recall_gain_ge_0_10": correct["mixed_target_recall"] - none["mixed_target_recall"] >= 0.10,
        "nuisance_fpr_not_worse": correct["nuisance_false_event_rate"] <= none["nuisance_false_event_rate"] + 1e-12,
        "balanced_utility_gain_vs_corrupted_ge_0_08": correct["balanced_utility"] - corrupt["balanced_utility"] >= 0.08,
        "target_only_recall_loss_le_0_05": none["target_only_recall"] - correct["target_only_recall"] <= 0.05,
    }
    promoted = all(criteria.values())

    return {
        "schema": "pollipi-latent-disturbance-v2-benchmark-v1",
        "master_seed": seed,
        "n_reps_per_scenario": n_reps,
        "scenarios": list(SCENARIOS),
        "reference_conditions": list(REFERENCE_CONDITIONS),
        "downstream_classifier": "unchanged PolliPi V1 pipeline.analyze default configuration",
        "metrics": metrics,
        "promotion_rule": {
            "criteria": criteria,
            "promoted_to_candidate_method": promoted,
        },
        "claim_boundary": (
            "Simulation-only. A positive result supports event-matched target-free reference information "
            "as a candidate nuisance-separation representation before the existing V1 classifier; it does "
            "not establish field wind inference, causal disturbance identity, or live-capture readiness."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(n_reps=args.n_reps, seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
