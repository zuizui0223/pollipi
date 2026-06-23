#!/usr/bin/env python3
"""
PolliPi overlapping-mesh simulation study: reproducible six-round reconstruction.

Purpose
-------
Reproduce the conceptual progression used in the exploratory rounds:
  R1  offset-mesh baseline
  R2  mixed conditions + overly conservative policy
  R3  trajectory-aware features
  R4  three-state decision policy
  R5  global motion + illumination compensation
  R6  rolling temporal-median background model

This is a synthetic calibration study. It does NOT establish field-ready
performance. Use the generated policy only in Pi "shadow mode" before any
adaptive interval changes are enabled.

Requirements
------------
Python >= 3.10
numpy
pandas
matplotlib

Run
---
python pollipi_mesh_simulation_rounds.py --output results

Outputs
-------
results/
  round_summary.csv
  overall_summary.md
  round_01_baseline/
  ...
  round_06_rolling_background/
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from itertools import product
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# Reproducibility settings
# ---------------------------------------------------------------------
SEED = 20260623
H, W = 72, 112
ROWS, COLS = 6, 8
CELL_H, CELL_W = H // ROWS, W // COLS
N_FRAMES = 16
N_REPS = 24


@dataclass(frozen=True)
class RoundSpec:
    number: int
    slug: str
    title: str
    compensation: str
    decision_mode: str
    active_thresholds: Tuple[float, ...]
    use_offset_mesh: bool
    use_global_registration: bool
    use_rolling_background: bool
    target_signal_weight: float
    false_strong_penalty: float
    false_any_penalty: float


SCENARIOS: Dict[str, str] = {
    "wind": "noise",
    "local_sway": "noise",
    "shadow": "noise",
    "camera_shake": "noise",
    "target_clean": "target",
    "target_edge": "target",
    "target_low_snr": "target",
    "target_wind": "target",
    "target_shadow": "target",
    "target_local_sway": "target",
    "target_wind_shadow": "target",
}


ROUNDS = [
    RoundSpec(
        1, "baseline", "R1: offset-mesh baseline",
        "none", "binary", (0.030, 0.045),
        True, False, False, 0.55, 1.00, 0.00,
    ),
    RoundSpec(
        2, "mixed_conservative", "R2: mixed conditions, conservative binary policy",
        "none", "binary", (0.024, 0.030, 0.045),
        True, False, False, 0.60, 1.20, 0.00,
    ),
    RoundSpec(
        3, "trajectory_aware", "R3: trajectory-aware binary policy",
        "none", "binary", (0.018, 0.024, 0.030),
        True, False, False, 0.62, 1.20, 0.00,
    ),
    RoundSpec(
        4, "three_state", "R4: three-state policy",
        "none", "three_state", (0.012, 0.018, 0.024),
        True, False, False, 0.55, 1.60, 0.25,
    ),
    RoundSpec(
        5, "global_compensation", "R5: global registration + illumination compensation",
        "global_registration_and_brightness", "three_state", (0.010, 0.015, 0.020),
        True, True, False, 0.55, 1.50, 0.20,
    ),
    RoundSpec(
        6, "rolling_background", "R6: global registration + rolling median background",
        "global_registration_and_rolling_background", "three_state", (0.012, 0.018, 0.024),
        True, True, True, 0.58, 1.50, 0.15,
    ),
]


# ---------------------------------------------------------------------
# Synthetic image generation
# ---------------------------------------------------------------------
def base_scene(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    frame = 0.48 + 0.055 * np.sin(xx / 7.1) + 0.04 * np.cos(yy / 5.3)
    for _ in range(12):
        cx, cy = rng.uniform(0, W), rng.uniform(0, H)
        sx, sy = rng.uniform(3.5, 14), rng.uniform(3.5, 14)
        amp = rng.uniform(-0.09, 0.10)
        frame += amp * np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) / 2)
    return np.clip(frame, 0, 1)


def shift_image(image: np.ndarray, dx: float, dy: float) -> np.ndarray:
    ix, iy = int(round(dx)), int(round(dy))
    out = np.zeros_like(image)
    sy0, sy1 = max(0, -iy), min(H, H - iy)
    sx0, sx1 = max(0, -ix), min(W, W - ix)
    dy0, dy1 = max(0, iy), min(H, H + iy)
    dx0, dx1 = max(0, ix), min(W, W + ix)
    out[dy0:dy1, dx0:dx1] = image[sy0:sy1, sx0:sx1]
    return out


def add_target(image: np.ndarray, x: float, y: float, amp: float, radius: float) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W]
    blob = amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * radius ** 2))
    return np.clip(image + blob, 0, 1)


def add_shadow(image: np.ndarray, t: int, frames: int, strength: float = 0.22) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W]
    center = -14 + (W + 28) * t / max(frames - 1, 1)
    shadow = strength / (1 + np.exp(-(xx - center) / 5.0))
    return np.clip(image - shadow, 0, 1)


def local_sway(image: np.ndarray, t: int) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W]
    weight = np.exp(-((xx - W * 0.48) ** 2 + (yy - H * 0.54) ** 2) / (2 * 22 ** 2))
    movement = 3.0 * np.sin(2 * np.pi * t / 4.8)
    moved = shift_image(image, movement, 0.3 * movement)
    return np.clip((1 - weight) * image + weight * moved, 0, 1)


def generate_sequence(name: str, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    scene = base_scene(seed)
    x0, y0 = rng.uniform(10, W - 26), rng.uniform(12, H - 18)
    theta = rng.uniform(-0.65, 0.65)
    speed = rng.uniform(0.8, 1.55)
    frames = []

    for t in range(N_FRAMES):
        frame = scene.copy()

        if name in {"wind", "target_wind", "target_wind_shadow"}:
            dx = 2.2 * np.sin(2 * np.pi * t / 5.8)
            frame = shift_image(frame, dx, 0.3 * dx)

        if name in {"local_sway", "target_local_sway"}:
            frame = local_sway(frame, t)

        if name in {"shadow", "target_shadow", "target_wind_shadow"}:
            frame = add_shadow(frame, t, N_FRAMES)

        if name == "camera_shake":
            frame = shift_image(frame, rng.normal(0, 1.8), rng.normal(0, 1.1))

        if name.startswith("target_"):
            if name == "target_edge":
                x = -2 + (W + 4) * t / max(N_FRAMES - 1, 1)
                y = H * 0.58 + 3 * np.sin(t / 2.5)
            else:
                x = x0 + speed * t * np.cos(theta) + 2 * np.sin(t / 3.2)
                y = y0 + speed * t * np.sin(theta) + 1.7 * np.cos(t / 4.4)
            amp = 0.20 if name == "target_low_snr" else 0.52
            radius = 1.25 if name == "target_low_snr" else 1.75
            frame = add_target(frame, x, y, amp, radius)

        noise_sigma = 0.020 if name == "target_low_snr" else 0.010
        frame += rng.normal(0, noise_sigma, frame.shape)
        frames.append(np.clip(frame, 0, 1))

    return np.asarray(frames)


# ---------------------------------------------------------------------
# Registration, background modelling, and mesh feature extraction
# ---------------------------------------------------------------------
def estimate_global_shift(prev: np.ndarray, curr: np.ndarray, max_shift: int = 3) -> Tuple[int, int]:
    p = prev - np.median(prev)
    c = curr - np.median(curr)
    border = max_shift + 1
    best = (np.inf, 0, 0)

    for dy in range(-max_shift, max_shift + 1):
        for dx in range(-max_shift, max_shift + 1):
            aligned = shift_image(c, -dx, -dy)
            error = np.mean(
                (p[border:-border, border:-border] - aligned[border:-border, border:-border]) ** 2
            )
            if error < best[0]:
                best = (error, dx, dy)
    return best[1], best[2]


def normalize_brightness(reference: np.ndarray, target: np.ndarray) -> np.ndarray:
    return np.clip(target - np.median(target) + np.median(reference), 0, 1)


def residual_frames(sequence: np.ndarray, spec: RoundSpec) -> Tuple[List[np.ndarray], List[float]]:
    """
    Return residual images between adjacent or rolling-background frames.
    """
    residuals: List[np.ndarray] = []
    shifts: List[float] = []

    if not spec.use_rolling_background:
        for idx in range(1, len(sequence)):
            prev = sequence[idx - 1]
            curr = sequence[idx]

            if spec.use_global_registration:
                dx, dy = estimate_global_shift(prev, curr)
                curr = normalize_brightness(prev, shift_image(curr, -dx, -dy))
                shifts.append(float(np.hypot(dx, dy)))
            else:
                shifts.append(0.0)

            residuals.append(np.abs(curr - prev))
        return residuals, shifts

    registered: List[np.ndarray] = [sequence[0]]
    reference = sequence[0]

    for idx in range(1, len(sequence)):
        dx, dy = estimate_global_shift(reference, sequence[idx])
        current = shift_image(sequence[idx], -dx, -dy)
        bg = np.median(np.stack(registered[max(0, len(registered) - 4):]), axis=0)
        current = normalize_brightness(bg, current)
        residuals.append(np.abs(current - bg))
        shifts.append(float(np.hypot(dx, dy)))
        registered.append(current)

    return residuals, shifts


def mesh_values(residual: np.ndarray, offset: bool) -> np.ndarray:
    if offset:
        residual = np.roll(residual, (CELL_H // 2, CELL_W // 2), axis=(0, 1))
    blocks = residual.reshape(ROWS, CELL_H, COLS, CELL_W).transpose(0, 2, 1, 3)
    # Upper-tail/max proxy retains a tiny compact target that cell means would erase.
    return blocks.max(axis=(2, 3))


def largest_component(mask: np.ndarray) -> int:
    visited = np.zeros_like(mask, dtype=bool)
    maximum = 0

    for row in range(ROWS):
        for col in range(COLS):
            if not mask[row, col] or visited[row, col]:
                continue
            stack = [(row, col)]
            visited[row, col] = True
            size = 0

            while stack:
                rr, cc = stack.pop()
                size += 1
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = rr + dr, cc + dc
                    if (
                        0 <= nr < ROWS
                        and 0 <= nc < COLS
                        and mask[nr, nc]
                        and not visited[nr, nc]
                    ):
                        visited[nr, nc] = True
                        stack.append((nr, nc))
            maximum = max(maximum, size)
    return maximum


def weighted_centroid(activity: np.ndarray) -> np.ndarray:
    total = activity.sum()
    if total <= 1e-12:
        return np.array([np.nan, np.nan])
    rr, cc = np.mgrid[0:ROWS, 0:COLS]
    return np.array([(rr * activity).sum() / total, (cc * activity).sum() / total])


def max_consecutive_run(values: np.ndarray) -> int:
    current = 0
    best = 0
    for value in values:
        current = current + 1 if value else 0
        best = max(best, current)
    return best


def extract_features(sequence: np.ndarray, spec: RoundSpec, active_threshold: float) -> Dict[str, float]:
    residuals, global_shifts = residual_frames(sequence, spec)

    primary = np.asarray([mesh_values(residual, False) for residual in residuals])
    if spec.use_offset_mesh:
        secondary = np.asarray([mesh_values(residual, True) for residual in residuals])
    else:
        secondary = primary.copy()

    # Common-mode subtraction is intentionally only spatial: it removes frame-wide
    # changes but preserves localized cells.
    primary_residual = np.clip(
        primary - np.median(primary, axis=(1, 2), keepdims=True), 0, None
    )
    secondary_residual = np.clip(
        secondary - np.median(secondary, axis=(1, 2), keepdims=True), 0, None
    )

    masks = primary_residual >= active_threshold
    active_proportion = masks.mean(axis=(1, 2))

    concentration = []
    centroids = []
    for mask, values in zip(masks, primary_residual):
        n_active = int(mask.sum())
        concentration.append(largest_component(mask) / n_active if n_active else 0.0)
        centroids.append(weighted_centroid(values))
    concentration = np.asarray(concentration)
    centroids = np.asarray(centroids)

    e_primary = primary_residual.sum(axis=(1, 2))
    e_secondary = secondary_residual.sum(axis=(1, 2))
    offset_agreement = np.minimum(e_primary, e_secondary) / np.maximum(
        np.maximum(e_primary, e_secondary), 1e-9
    )

    valid = ~np.isnan(centroids[:, 0])
    vectors = []
    for idx in range(1, len(centroids)):
        if valid[idx] and valid[idx - 1]:
            vectors.append(centroids[idx] - centroids[idx - 1])
    vectors = np.asarray(vectors)
    step_lengths = np.linalg.norm(vectors, axis=1) if len(vectors) else np.array([])

    total_path = step_lengths.sum()
    net = (
        np.linalg.norm(centroids[valid][-1] - centroids[valid][0])
        if valid.sum() >= 2
        else 0.0
    )
    path_efficiency = float(net / max(total_path, 1e-9))

    reversal_count = 0
    reversal_denominator = 0
    for idx in range(1, len(vectors)):
        if np.linalg.norm(vectors[idx - 1]) > 1e-8 and np.linalg.norm(vectors[idx]) > 1e-8:
            reversal_denominator += 1
            reversal_count += int(np.dot(vectors[idx - 1], vectors[idx]) < 0)

    local_signal = (
        (active_proportion > 0)
        & (active_proportion < 0.25)
        & (concentration > 0.28)
    )

    return {
        "max_active_proportion": float(active_proportion.max()),
        "mean_active_proportion": float(active_proportion.mean()),
        "broad_frame_fraction": float((active_proportion >= 0.28).mean()),
        "mean_concentration": float(concentration.mean()),
        "mean_offset_agreement": float(offset_agreement.mean()),
        "persistence": float(max_consecutive_run(local_signal)),
        "mean_step": float(step_lengths.mean()) if len(step_lengths) else 0.0,
        "path_efficiency": path_efficiency,
        "reversal_rate": float(reversal_count / max(reversal_denominator, 1)),
        "mean_global_shift": float(np.mean(global_shifts)),
    }


# ---------------------------------------------------------------------
# Decision policies
# ---------------------------------------------------------------------
def classify_binary(features: Dict[str, float], params: Dict[str, float]) -> str:
    if (
        features["mean_global_shift"] >= params["global_shift"]
        or features["max_active_proportion"] >= params["broad_prop"]
        or features["broad_frame_fraction"] >= params["broad_fraction"]
    ):
        return "environmental_noise"

    if (
        features["mean_step"] >= params["osc_step"]
        and features["path_efficiency"] <= params["osc_efficiency"]
        and features["reversal_rate"] >= params["osc_reversal"]
    ):
        return "environmental_noise"

    if (
        features["persistence"] >= params["persist"]
        and features["mean_concentration"] >= params["concentration"]
        and features["mean_offset_agreement"] >= params["agreement"]
        and features["mean_step"] >= params["target_step"]
        and features["path_efficiency"] >= params["target_efficiency"]
    ):
        return "visitation_candidate"

    return "no_activity"


def classify_three_state(features: Dict[str, float], params: Dict[str, float]) -> str:
    if (
        features["mean_global_shift"] >= params["global_shift"]
        or features["max_active_proportion"] >= params["broad_prop"]
        or features["broad_frame_fraction"] >= params["broad_fraction"]
    ):
        return "environmental_noise"

    if (
        features["mean_step"] >= params["osc_step"]
        and features["path_efficiency"] <= params["osc_efficiency"]
        and features["reversal_rate"] >= params["osc_reversal"]
    ):
        return "environmental_noise"

    if (
        features["persistence"] >= params["strong_persist"]
        and features["mean_concentration"] >= params["strong_concentration"]
        and features["mean_offset_agreement"] >= params["strong_agreement"]
        and features["mean_step"] >= params["strong_step"]
        and features["path_efficiency"] >= params["strong_efficiency"]
    ):
        return "strong_visitation_candidate"

    if (
        features["persistence"] >= params["uncertain_persist"]
        and features["mean_concentration"] >= params["uncertain_concentration"]
        and features["mean_offset_agreement"] >= params["uncertain_agreement"]
    ):
        return "uncertain_local_activity"

    return "no_activity"


# ---------------------------------------------------------------------
# Search spaces
# ---------------------------------------------------------------------
def binary_parameter_space() -> List[Dict[str, float]]:
    values = product(
        [0.0, 1.2, 1.8],           # global_shift
        [0.24, 0.32],              # broad_prop
        [0.10, 0.20],              # broad_fraction
        [0.10, 0.18],              # oscillation step
        [0.45, 0.60],              # oscillation efficiency
        [0.35, 0.55],              # oscillation reversal
        [2, 3],                    # persistence
        [0.30, 0.45, 0.55],        # concentration
        [0.55, 0.70, 0.84],        # agreement
        [0.04, 0.10],              # target step
        [0.08, 0.20],              # target efficiency
    )
    keys = [
        "global_shift", "broad_prop", "broad_fraction",
        "osc_step", "osc_efficiency", "osc_reversal",
        "persist", "concentration", "agreement", "target_step", "target_efficiency",
    ]
    return [dict(zip(keys, row)) for row in values]


def three_state_parameter_space() -> List[Dict[str, float]]:
    values = product(
        [0.0, 1.2, 1.8],           # global_shift
        [0.24, 0.32],              # broad_prop
        [0.10, 0.20],              # broad_fraction
        [0.10, 0.18],              # oscillation step
        [0.45, 0.60],              # oscillation efficiency
        [0.35, 0.55],              # oscillation reversal
        [2, 3],                    # strong persistence
        [0.30, 0.45, 0.55],        # strong concentration
        [0.55, 0.70, 0.84],        # strong agreement
        [0.04, 0.10],              # strong step
        [0.08, 0.20],              # strong efficiency
        [2],                       # uncertain persistence
        [0.16, 0.28, 0.36],        # uncertain concentration
        [0.35, 0.55, 0.64],        # uncertain agreement
    )
    keys = [
        "global_shift", "broad_prop", "broad_fraction",
        "osc_step", "osc_efficiency", "osc_reversal",
        "strong_persist", "strong_concentration", "strong_agreement",
        "strong_step", "strong_efficiency",
        "uncertain_persist", "uncertain_concentration", "uncertain_agreement",
    ]
    return [dict(zip(keys, row)) for row in values]


# ---------------------------------------------------------------------
# Evaluation and outputs
# ---------------------------------------------------------------------
def evaluate_round(spec: RoundSpec, output_root: Path) -> Dict[str, object]:
    round_dir = output_root / f"round_{spec.number:02d}_{spec.slug}"
    round_dir.mkdir(parents=True, exist_ok=True)

    # Fixed synthetic dataset per round, but round-specific deterministic seed.
    raw_sequences = []
    for scenario_index, (name, truth) in enumerate(SCENARIOS.items()):
        for rep in range(N_REPS):
            seed = SEED + spec.number * 100_000 + scenario_index * 1_000 + rep
            raw_sequences.append((name, truth, generate_sequence(name, seed)))

    feature_cache: Dict[float, List[Tuple[str, str, Dict[str, float]]]] = {}
    for threshold in spec.active_thresholds:
        feature_cache[threshold] = [
            (name, truth, extract_features(sequence, spec, threshold))
            for name, truth, sequence in raw_sequences
        ]

    is_three_state = spec.decision_mode == "three_state"
    parameter_space = three_state_parameter_space() if is_three_state else binary_parameter_space()
    classifier: Callable[[Dict[str, float], Dict[str, float]], str] = (
        classify_three_state if is_three_state else classify_binary
    )

    search_rows = []
    best = None
    best_details = None

    for threshold, records in feature_cache.items():
        for params in parameter_space:
            predictions = [classifier(features, params) for _, _, features in records]
            truths = [truth for _, truth, _ in records]
            table = pd.DataFrame({"truth": truths, "prediction": predictions})
            targets = table[table["truth"] == "target"]
            noises = table[table["truth"] == "noise"]

            if is_three_state:
                strong_recall = float((targets["prediction"] == "strong_visitation_candidate").mean())
                any_target_signal = float(
                    targets["prediction"].isin(
                        ["strong_visitation_candidate", "uncertain_local_activity"]
                    ).mean()
                )
                false_strong = float((noises["prediction"] == "strong_visitation_candidate").mean())
                false_any = float(
                    noises["prediction"].isin(
                        ["strong_visitation_candidate", "uncertain_local_activity"]
                    ).mean()
                )
                noise_correct = float((noises["prediction"] == "environmental_noise").mean())
                score = (
                    0.40 * strong_recall
                    + spec.target_signal_weight * any_target_signal
                    + 0.30 * noise_correct
                    - spec.false_strong_penalty * false_strong
                    - spec.false_any_penalty * false_any
                )
                metrics = {
                    "strong_recall": strong_recall,
                    "any_target_signal": any_target_signal,
                    "false_strong": false_strong,
                    "false_any": false_any,
                    "noise_correct": noise_correct,
                    "score": score,
                }
            else:
                candidate_recall = float((targets["prediction"] == "visitation_candidate").mean())
                false_trigger = float((noises["prediction"] == "visitation_candidate").mean())
                noise_correct = float((noises["prediction"] == "environmental_noise").mean())
                score = (
                    spec.target_signal_weight * candidate_recall
                    + 0.35 * noise_correct
                    - spec.false_strong_penalty * false_trigger
                )
                metrics = {
                    "candidate_recall": candidate_recall,
                    "false_trigger": false_trigger,
                    "noise_correct": noise_correct,
                    "score": score,
                }

            row = {"active_threshold": threshold, **params, **metrics}
            search_rows.append(row)

            if best is None or score > best["score"]:
                best = row
                best_details = records

    search = pd.DataFrame(search_rows).sort_values("score", ascending=False).reset_index(drop=True)
    chosen_params = {
        key: value
        for key, value in best.items()
        if key not in {
            "active_threshold",
            "candidate_recall",
            "false_trigger",
            "strong_recall",
            "any_target_signal",
            "false_strong",
            "false_any",
            "noise_correct",
            "score",
        }
    }

    diagnostics = []
    for name, truth, features in best_details:
        decision = classifier(features, chosen_params)
        diagnostics.append({"scenario": name, "truth": truth, "decision": decision, **features})
    diagnostics = pd.DataFrame(diagnostics)

    labels = (
        ["strong_visitation_candidate", "uncertain_local_activity", "environmental_noise", "no_activity"]
        if is_three_state
        else ["visitation_candidate", "environmental_noise", "no_activity"]
    )

    grouped = diagnostics.groupby(["scenario", "truth"])
    rate_rows = []
    for (scenario, truth), group in grouped:
        row = {"scenario": scenario, "truth": truth, "n": len(group)}
        for label in labels:
            row[label] = float((group["decision"] == label).mean())
        rate_rows.append(row)
    scenario_rates = pd.DataFrame(rate_rows)

    # Save raw tables.
    search.head(250).to_csv(round_dir / "threshold_search_top250.csv", index=False)
    diagnostics.to_csv(round_dir / "per_sequence_features.csv", index=False)
    scenario_rates.to_csv(round_dir / "scenario_rates.csv", index=False)
    pd.DataFrame([best]).to_csv(round_dir / "selected_policy.csv", index=False)

    # Classification-rate plot.
    display_labels = labels
    pivot = scenario_rates.set_index("scenario")[display_labels]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(pivot))
    bottom = np.zeros(len(pivot))
    for label in display_labels:
        ax.bar(x, pivot[label], bottom=bottom, label=label)
        bottom += pivot[label].values
    ax.set_ylim(0, 1)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, rotation=28, ha="right")
    ax.set_ylabel("Proportion of synthetic sequences")
    ax.set_title(spec.title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(round_dir / "classification_rates.png", dpi=180)
    plt.close(fig)

    # Trade-off plot.
    fig, ax = plt.subplots(figsize=(7, 5))
    if is_three_state:
        ax.scatter(search["false_strong"], search["any_target_signal"], s=8, alpha=0.18)
        ax.scatter(
            [best["false_strong"]], [best["any_target_signal"]],
            s=85, label="selected policy"
        )
        ax.set_xlabel("False strong-candidate rate in noise")
        ax.set_ylabel("Any target signal rate (strong + uncertain)")
    else:
        ax.scatter(search["false_trigger"], search["candidate_recall"], s=8, alpha=0.18)
        ax.scatter(
            [best["false_trigger"]], [best["candidate_recall"]],
            s=85, label="selected policy"
        )
        ax.set_xlabel("False candidate rate in noise")
        ax.set_ylabel("Candidate recall in target-containing sequences")
    ax.set_title(f"{spec.title}: policy search trade-off")
    ax.legend()
    fig.tight_layout()
    fig.savefig(round_dir / "policy_tradeoff.png", dpi=180)
    plt.close(fig)

    # Round-specific human-readable note.
    round_note = f"""# {spec.title}

## Method
- Compensation: `{spec.compensation}`
- Decision mode: `{spec.decision_mode}`
- Offset mesh: `{spec.use_offset_mesh}`
- Global registration: `{spec.use_global_registration}`
- Rolling background: `{spec.use_rolling_background}`

## Selected policy
```text
{pd.Series(best).to_string()}
```

## Warning
This is synthetic calibration only. Do not copy the selected thresholds to a
field Pi and enable adaptive intervals directly. First run the exact feature
pipeline in shadow mode on real fixed-interval Pi sequences.
"""
    (round_dir / "README.md").write_text(round_note, encoding="utf-8")

    summary = {
        "round": spec.number,
        "slug": spec.slug,
        "title": spec.title,
        "decision_mode": spec.decision_mode,
        "compensation": spec.compensation,
        "best_score": float(best["score"]),
        "noise_correct": float(best["noise_correct"]),
        "active_threshold": float(best["active_threshold"]),
        **(
            {
                "strong_recall": float(best["strong_recall"]),
                "any_target_signal": float(best["any_target_signal"]),
                "false_strong": float(best["false_strong"]),
                "false_any": float(best["false_any"]),
            }
            if is_three_state
            else {
                "candidate_recall": float(best["candidate_recall"]),
                "false_trigger": float(best["false_trigger"]),
            }
        ),
    }
    return summary


def write_overall_summary(summary: pd.DataFrame, output_root: Path) -> None:
    summary.to_csv(output_root / "round_summary.csv", index=False)

    lines = [
        "# PolliPi six-round synthetic mesh simulation: results summary",
        "",
        "## What this does reproduce",
        "",
        "- A deterministic synthetic test bed with target trajectories, wind, local sway, shadow, and camera shake.",
        "- The conceptual transition from simple offset meshes to three-state policies and compensation/background models.",
        "- Per-round threshold searches, scenario-level rates, and plots.",
        "",
        "## What this does not prove",
        "",
        "- Field-ready visitation detection accuracy.",
        "- That a target is biologically a pollinator or a confirmed visit.",
        "- That any selected threshold should immediately control a Raspberry Pi.",
        "",
        "## Cross-round interpretation",
        "",
        "The useful finding is not a single final threshold. The rounds show a recurring trade-off:",
        "",
        "1. Strong broad-noise rejection is achievable with mesh features.",
        "2. Clean and boundary-crossing targets can be retained.",
        "3. Mixed wind/shadow/local-sway + target conditions remain difficult in synthetic data.",
        "4. Aggressive temporal-median background modelling can suppress weak moving targets.",
        "",
        "Therefore the safe field architecture is:",
        "",
        "```text",
        "environmental_noise          -> retain baseline interval or cautiously lengthen",
        "no_activity                  -> move gradually toward longer interval",
        "uncertain_local_activity     -> keep baseline interval; log only",
        "strong_visitation_candidate  -> shorten next interval only",
        "```",
        "",
        "## Next validation step",
        "",
        "Run the exact feature pipeline in Pi shadow mode on real fixed-interval sequences:",
        "",
        "```text",
        "1. Do not alter interval.",
        "2. Write mesh features and decisions to metadata.",
        "3. Manually review scheduled images.",
        "4. Compare decisions with actual visible insect/visit evidence.",
        "5. Recalibrate thresholds and only then enable adaptive scheduling.",
        "```",
        "",
        "## Round-level results",
        "",
        summary.to_markdown(index=False),
        "",
    ]
    (output_root / "overall_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("pollipi_mesh_results"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    summaries = []
    for spec in ROUNDS:
        print(f"Running round {spec.number}: {spec.title}")
        summaries.append(evaluate_round(spec, args.output))

    summary = pd.DataFrame(summaries)
    write_overall_summary(summary, args.output)
    print("\nDone.")
    print(f"Results written to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
