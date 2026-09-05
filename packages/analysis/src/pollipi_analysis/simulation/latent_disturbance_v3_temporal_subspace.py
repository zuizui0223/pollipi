"""V3 simulation: spatially non-corresponding temporal nuisance subspace.

A target-free reference sequence defines only a temporal basis. That basis is
projected from the primary sequence before the unchanged PolliPi V1 observer.
Protocol: ``docs/LATENT_DISTURBANCE_V3_TEMPORAL_SUBSPACE.md``.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.schemas.states import STRONG_VISITATION_CANDIDATE, UNCERTAIN_LOCAL_ACTIVITY

MASTER_SEED = 20260905
DEFAULT_REPS = 48
T = 9
TEMPORAL_RANK = 3
SIZE = (128, 192)
TARGET_FRAMES = np.array([False, False, True, True, True, True, True, False, False], dtype=bool)
CONDITIONS = ("matched_temporal_reference", "time_permuted_reference", "no_reference")
TARGET_SCENARIOS = (
    "target_only",
    "target_plus_wind",
    "target_plus_shadow",
    "target_plus_shake",
    "target_plus_local_sway",
)
MIXED_TARGET_SCENARIOS = TARGET_SCENARIOS[1:]
NOISE_SCENARIOS = ("wind_only", "shadow_only", "shake_only", "local_sway_only")
BROAD_NOISE_SCENARIOS = ("wind_only", "shadow_only", "shake_only")
SCENARIOS = TARGET_SCENARIOS + NOISE_SCENARIOS


@dataclass(frozen=True)
class TemporalWorld:
    scenario: str
    primary_background: np.ndarray
    reference_background: np.ndarray
    primary_frames: np.ndarray
    reference_frames: np.ndarray
    target_mask: np.ndarray
    nuisance: str | None


def _background(rng: np.random.Generator, size: tuple[int, int] = SIZE, *, reverse: bool = False) -> np.ndarray:
    h, w = size
    x = np.linspace(-18, 18, w, dtype=np.float32)
    y = np.linspace(-7, 7, h, dtype=np.float32)
    base = 98.0 + x[None, :] + y[:, None]
    texture = rng.normal(0, 2.2, size=(h, w)).astype(np.float32)
    if reverse:
        base = np.flip(base, axis=1)
        texture = np.flip(texture, axis=0)
    return (base + texture).astype(np.float32)


def _disc(shape: tuple[int, int], cy: int, cx: int, radius: int, amplitude: float) -> np.ndarray:
    yy, xx = np.ogrid[: shape[0], : shape[1]]
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
    out = np.zeros(shape, dtype=np.float32)
    out[mask] = amplitude
    return out


def _target_sequence(rng: np.random.Generator, shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    out = np.zeros((T, h, w), dtype=np.float32)
    xs = np.linspace(int(w * 0.28), int(w * 0.58), int(np.sum(TARGET_FRAMES))).astype(int)
    y0 = int(h * 0.56 + rng.integers(-3, 4))
    amp = float(rng.uniform(68.0, 80.0))
    radius = int(rng.integers(5, 7))
    j = 0
    for t in range(T):
        if TARGET_FRAMES[t]:
            out[t] = _disc(shape, y0 + int(rng.integers(-1, 2)), int(xs[j]), radius, amp)
            j += 1
    return out


def _wind_sequences(rng: np.random.Generator, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    h, w = shape
    tt = np.arange(T, dtype=np.float32)
    phase = float(rng.uniform(-0.4, 0.4))
    u1 = np.sin(2 * np.pi * tt / T + phase)
    u2 = 0.55 * np.cos(4 * np.pi * tt / T + phase / 2)
    x = np.linspace(0, 2 * np.pi, w, dtype=np.float32)
    y = np.linspace(0, 2 * np.pi, h, dtype=np.float32)
    p1 = np.sin(x + float(rng.uniform(-0.4, 0.4)))[None, :]
    p1 = np.broadcast_to(p1, (h, w))
    p2 = np.cos(y + float(rng.uniform(-0.4, 0.4)))[:, None]
    p2 = np.broadcast_to(p2, (h, w))
    r1 = np.sin(x + float(rng.uniform(0.9, 1.8)))[None, :]
    r1 = np.broadcast_to(r1, (h, w))
    r2 = np.cos(y + float(rng.uniform(0.8, 1.7)))[:, None]
    r2 = np.broadcast_to(r2, (h, w))
    gain = float(rng.uniform(0.82, 1.18))
    primary = np.stack([25.0 * u1[t] * p1 + 11.0 * u2[t] * p2 for t in range(T)]).astype(np.float32)
    reference = np.stack([gain * (24.0 * u1[t] * r1 + 10.0 * u2[t] * r2) for t in range(T)]).astype(np.float32)
    return primary, reference


def _shadow_sequences(rng: np.random.Generator, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    h, w = shape
    tt = np.arange(T, dtype=np.float32)
    driver = 0.15 + 0.85 * (0.5 + 0.5 * np.sin(2 * np.pi * tt / T - 0.7))
    pmask = np.zeros(shape, dtype=np.float32)
    rmask = np.zeros(shape, dtype=np.float32)
    pmask[:, int(w * 0.10):int(w * 0.68)] = 1.0
    rmask[:, int(w * 0.38):int(w * 0.94)] = 1.0
    gain = float(rng.uniform(0.82, 1.18))
    primary = np.stack([-30.0 * driver[t] * pmask for t in range(T)]).astype(np.float32)
    reference = np.stack([-30.0 * gain * driver[t] * rmask for t in range(T)]).astype(np.float32)
    return primary, reference


def _shake_sequences(
    rng: np.random.Generator,
    primary_bg: np.ndarray,
    reference_bg: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    tt = np.arange(T, dtype=np.float32)
    phase = float(rng.uniform(-0.3, 0.3))
    dxs = np.rint(3.0 * np.sin(2 * np.pi * tt / T + phase)).astype(int)
    dys = np.rint(2.0 * np.cos(2 * np.pi * tt / T + phase)).astype(int)
    primary = []
    reference = []
    for dx, dy in zip(dxs, dys):
        p = np.roll(np.roll(primary_bg, int(dy), axis=0), int(dx), axis=1) - primary_bg
        # Same camera-motion time course but a spatially different scene texture.
        r = np.roll(np.roll(reference_bg, int(dy), axis=0), int(dx), axis=1) - reference_bg
        primary.append(p)
        reference.append(r)
    gain = float(rng.uniform(0.90, 1.10))
    return np.stack(primary).astype(np.float32), (gain * np.stack(reference)).astype(np.float32)


def _local_sway_sequences(rng: np.random.Generator, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    h, w = shape
    tt = np.arange(T, dtype=np.float32)
    phase = float(rng.uniform(-0.25, 0.25))
    sway = np.sin(2 * np.pi * tt / T + phase)
    vertical = np.cos(2 * np.pi * tt / T + phase)
    primary = np.zeros((T, h, w), dtype=np.float32)
    reference = np.zeros((T, h, w), dtype=np.float32)
    p0 = (int(h * 0.31), int(w * 0.75))
    r0 = (int(h * 0.73), int(w * 0.70))
    p_amp = float(rng.uniform(31.0, 38.0))
    r_amp = p_amp * float(rng.uniform(0.82, 1.18))
    for t in range(T):
        py = p0[0] + int(np.rint(2.0 * vertical[t]))
        px = p0[1] + int(np.rint(6.0 * sway[t]))
        ry = r0[0] + int(np.rint(2.5 * vertical[t]))
        rx = r0[1] + int(np.rint(7.0 * sway[t]))
        primary[t] = _disc(shape, py, px, 8, p_amp)
        reference[t] = _disc(shape, ry, rx, 9, r_amp)
    return primary, reference


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


def generate_temporal_world(scenario: str, seed: int) -> TemporalWorld:
    has_target, nuisance = _scenario_parts(scenario)
    rng = np.random.default_rng(seed)
    pbg = _background(rng, reverse=False)
    rbg = _background(np.random.default_rng(seed + 1_000_003), reverse=True)
    shape = pbg.shape
    zero = np.zeros((T, *shape), dtype=np.float32)

    if nuisance is None:
        pn, rn = zero.copy(), zero.copy()
    elif nuisance == "wind":
        pn, rn = _wind_sequences(rng, shape)
    elif nuisance == "shadow":
        pn, rn = _shadow_sequences(rng, shape)
    elif nuisance == "shake":
        pn, rn = _shake_sequences(rng, pbg, rbg)
    elif nuisance == "local_sway":
        pn, rn = _local_sway_sequences(rng, shape)
    else:
        raise ValueError(nuisance)

    target = _target_sequence(rng, shape) if has_target else zero.copy()
    primary_sensor_noise = rng.normal(0.0, 0.8, size=(T, *shape)).astype(np.float32)
    ref_rng = np.random.default_rng(seed + 2_000_003)
    reference_sensor_noise = ref_rng.normal(0.0, 1.5, size=(T, *shape)).astype(np.float32)

    primary = np.clip(pbg[None, :, :] + pn + target + primary_sensor_noise, 0, 255).astype(np.float32)
    reference = np.clip(rbg[None, :, :] + rn + reference_sensor_noise, 0, 255).astype(np.float32)
    return TemporalWorld(
        scenario=scenario,
        primary_background=pbg,
        reference_background=rbg,
        primary_frames=primary,
        reference_frames=reference,
        target_mask=TARGET_FRAMES.copy() if has_target else np.zeros(T, dtype=bool),
        nuisance=nuisance,
    )


def _permutation(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    perm = rng.permutation(T)
    if np.array_equal(perm, np.arange(T)):
        perm = np.roll(perm, 1)
    return perm


def temporal_subspace_project(
    primary_frames: np.ndarray,
    primary_background: np.ndarray,
    reference_frames: np.ndarray,
    reference_background: np.ndarray,
    *,
    rank: int = TEMPORAL_RANK,
) -> tuple[np.ndarray, dict[str, float]]:
    """Remove primary temporal components lying in the target-free reference subspace."""
    p = np.asarray(primary_frames, dtype=np.float64) - np.asarray(primary_background, dtype=np.float64)[None, :, :]
    r = np.asarray(reference_frames, dtype=np.float64) - np.asarray(reference_background, dtype=np.float64)[None, :, :]
    pm = p.reshape(T, -1)
    rm = r.reshape(T, -1)
    u, s, _ = np.linalg.svd(rm, full_matrices=False)
    k = max(1, min(int(rank), u.shape[1]))
    basis = u[:, :k]
    explained = basis @ (basis.T @ pm)
    residual = pm - explained
    denom = float(np.sum(pm * pm))
    explained_fraction = float(np.sum(explained * explained) / denom) if denom > 1e-12 else 0.0
    reference_energy = float(np.sum(rm * rm))
    retained_reference_fraction = float(np.sum(s[:k] ** 2) / reference_energy) if reference_energy > 1e-12 else 0.0
    corrected = np.asarray(primary_background, dtype=np.float64)[None, :, :] + residual.reshape(p.shape)
    return np.clip(corrected, 0, 255).astype(np.float32), {
        "explained_primary_energy_fraction": explained_fraction,
        "retained_reference_energy_fraction": retained_reference_fraction,
        "reference_top_singular_value": float(s[0]) if s.size else 0.0,
    }


def _is_local_candidate(state: str) -> bool:
    return state in (UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE)


def _has_two_consecutive(values: list[bool]) -> bool:
    return any(values[i] and values[i + 1] for i in range(len(values) - 1))


def _evaluate_sequence(frames: np.ndarray, world: TemporalWorld) -> dict[str, Any]:
    candidates: list[bool] = []
    states: list[str] = []
    for frame in frames:
        decision = analyze(frame, world.primary_background)
        states.append(decision.state)
        candidates.append(_is_local_candidate(decision.state))

    target_idx = np.flatnonzero(world.target_mask)
    if target_idx.size:
        target_frame_recall = float(np.mean([candidates[int(i)] for i in target_idx]))
        target_episode_detected = sum(candidates[int(i)] for i in target_idx) >= 2
    else:
        target_frame_recall = None
        target_episode_detected = None
    return {
        "states": states,
        "local_candidate_frames": int(sum(candidates)),
        "all_frame_local_rate": float(np.mean(candidates)),
        "target_frame_recall": target_frame_recall,
        "target_episode_detected": target_episode_detected,
        "two_consecutive_local": _has_two_consecutive(candidates),
    }


def evaluate_temporal_subspace(*, n_reps: int = DEFAULT_REPS, seed: int = MASTER_SEED) -> dict[str, Any]:
    if n_reps <= 0:
        raise ValueError("n_reps must be positive")

    scenario_records: dict[str, dict[str, list[dict[str, Any]]]] = {
        condition: {scenario: [] for scenario in SCENARIOS}
        for condition in CONDITIONS
    }

    for scenario_index, scenario in enumerate(SCENARIOS):
        for rep in range(n_reps):
            world_seed = seed + scenario_index * 100_000 + rep
            world = generate_temporal_world(scenario, world_seed)
            perm = _permutation(seed + 40_000_000 + scenario_index * 100_000 + rep)

            matched_frames, matched_diag = temporal_subspace_project(
                world.primary_frames,
                world.primary_background,
                world.reference_frames,
                world.reference_background,
            )
            permuted_frames, perm_diag = temporal_subspace_project(
                world.primary_frames,
                world.primary_background,
                world.reference_frames[perm],
                world.reference_background,
            )
            conditions = {
                "matched_temporal_reference": (matched_frames, matched_diag),
                "time_permuted_reference": (permuted_frames, perm_diag),
                "no_reference": (
                    world.primary_frames,
                    {
                        "explained_primary_energy_fraction": 0.0,
                        "retained_reference_energy_fraction": 0.0,
                        "reference_top_singular_value": 0.0,
                    },
                ),
            }
            for condition, (frames, diag) in conditions.items():
                record = _evaluate_sequence(frames, world)
                record.update(diag)
                scenario_records[condition][scenario].append(record)

    metrics: dict[str, Any] = {}
    for condition in CONDITIONS:
        per_scenario: dict[str, Any] = {}
        for scenario in SCENARIOS:
            records = scenario_records[condition][scenario]
            target_recalls = [r["target_frame_recall"] for r in records if r["target_frame_recall"] is not None]
            target_episodes = [bool(r["target_episode_detected"]) for r in records if r["target_episode_detected"] is not None]
            per_scenario[scenario] = {
                "target_frame_recall": float(np.mean(target_recalls)) if target_recalls else None,
                "all_frame_local_rate": float(np.mean([r["all_frame_local_rate"] for r in records])),
                "target_episode_recall": float(np.mean(target_episodes)) if target_episodes else None,
                "two_consecutive_local_rate": float(np.mean([r["two_consecutive_local"] for r in records])),
                "explained_primary_energy_fraction_mean": float(np.mean([r["explained_primary_energy_fraction"] for r in records])),
                "retained_reference_energy_fraction_mean": float(np.mean([r["retained_reference_energy_fraction"] for r in records])),
            }

        mixed_recall = float(np.mean([per_scenario[s]["target_frame_recall"] for s in MIXED_TARGET_SCENARIOS]))
        target_only_recall = float(per_scenario["target_only"]["target_frame_recall"])
        nuisance_fpr = float(np.mean([per_scenario[s]["all_frame_local_rate"] for s in NOISE_SCENARIOS]))
        local_sway_fpr = float(per_scenario["local_sway_only"]["all_frame_local_rate"])
        broad_fpr = float(np.mean([per_scenario[s]["all_frame_local_rate"] for s in BROAD_NOISE_SCENARIOS]))
        target_episode_recall = float(np.mean([per_scenario[s]["target_episode_recall"] for s in TARGET_SCENARIOS]))
        nuisance_false_episode = float(np.mean([per_scenario[s]["two_consecutive_local_rate"] for s in NOISE_SCENARIOS]))
        metrics[condition] = {
            "mixed_target_frame_recall": mixed_recall,
            "target_only_frame_recall": target_only_recall,
            "nuisance_false_frame_rate": nuisance_fpr,
            "local_sway_false_frame_rate": local_sway_fpr,
            "broad_nuisance_false_frame_rate": broad_fpr,
            "target_episode_recall": target_episode_recall,
            "nuisance_false_episode_rate": nuisance_false_episode,
            "balanced_utility": (mixed_recall + (1.0 - nuisance_fpr)) / 2.0,
            "per_scenario": per_scenario,
        }

    matched = metrics["matched_temporal_reference"]
    permuted = metrics["time_permuted_reference"]
    none = metrics["no_reference"]
    criteria = {
        "matched_mixed_recall_gain_vs_none_ge_0_15": matched["mixed_target_frame_recall"] - none["mixed_target_frame_recall"] >= 0.15,
        "matched_nuisance_fpr_reduction_vs_none_ge_0_10": none["nuisance_false_frame_rate"] - matched["nuisance_false_frame_rate"] >= 0.10,
        "matched_balanced_utility_gain_vs_permuted_ge_0_10": matched["balanced_utility"] - permuted["balanced_utility"] >= 0.10,
        "matched_target_only_loss_le_0_05": none["target_only_frame_recall"] - matched["target_only_frame_recall"] <= 0.05 + 1e-12,
        "matched_local_sway_fpr_reduction_vs_none_ge_0_30": none["local_sway_false_frame_rate"] - matched["local_sway_false_frame_rate"] >= 0.30,
        "matched_broad_fpr_within_none_plus_0_05": matched["broad_nuisance_false_frame_rate"] <= none["broad_nuisance_false_frame_rate"] + 0.05 + 1e-12,
    }

    return {
        "schema": "pollipi-latent-disturbance-v3-temporal-subspace-v1",
        "master_seed": seed,
        "n_reps_per_scenario": n_reps,
        "sequence_length": T,
        "temporal_rank": TEMPORAL_RANK,
        "target_frame_indices": np.flatnonzero(TARGET_FRAMES).tolist(),
        "conditions": list(CONDITIONS),
        "scenarios": list(SCENARIOS),
        "downstream_classifier": "unchanged PolliPi V1 pipeline.analyze default configuration",
        "metrics": metrics,
        "promotion_rule": {
            "criteria": criteria,
            "promoted_to_temporal_reference_candidate": all(criteria.values()),
        },
        "claim_boundary": (
            "Simulation-only. A positive result supports a spatially non-corresponding target-free temporal "
            "reference subspace as a candidate nuisance representation; it does not identify physical wind, "
            "certify biological absence, or authorize live adaptive capture."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_temporal_subspace(n_reps=args.n_reps, seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
