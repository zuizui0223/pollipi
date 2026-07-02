"""Connect the R5 synthetic sequences to the actual Mode-③ Pi runtime.

The bridge runs the *exact* Pi runtime decision path on each consecutive frame
pair — ``pollipi_analysis.pipeline.analyze`` — and feeds the resulting per-probe
decision states into the *same* ``ThreeStageController`` (video mode) the Pi uses.
It then searches only the Pi-loadable ``FeatureConfig`` / ``ClassifierConfig``
parameters and writes the best as ``mode3_runtime_bridge_policy_v1.json`` via
``pollipi_analysis.policy.artifact.write_policy``. This is the SINGLE official
policy-export path for the Pi runtime (the legacy pairwise search in
``simulation/run.py`` writes a separate ``legacy_pairwise_policy.json``).

Scale note: the R5 study renders at 72x112 in [0, 1], but the Pi runtime's
``cell_size`` (px) and ``pixel_difference`` (0-255) live at the camera luminance
scale. Each frame is therefore bilinearly resized to LUMA_SIZE and scaled to
0-255 before ``analyze`` (cell_size=32 -> a 6x8 mesh, matching the study grid and
keeping the search tractable). This is a synthetic proxy for the Pi lores stream,
so ``validation_status`` stays ``simulation_informed`` — never field validated.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any, Iterator, Optional

import numpy as np

from pollipi_analysis.pipeline import PipelineConfig, analyze
from pollipi_analysis.policy.artifact import PolicyMeta, write_policy
from pollipi_analysis.policy.three_stage import HIGH, MID, ThreeStageConfig, ThreeStageController
from pollipi_analysis.schemas.states import STRONG_VISITATION_CANDIDATE
from pollipi_analysis.simulation.r5_scenarios import SCENARIOS, SEED, generate_sequence

# Render scale: a tractable proxy for the Pi lores stream (see module docstring).
LUMA_H, LUMA_W = 192, 256
PROBE_SEC = 5.0  # the Pi probes every 5 s; states are fed at this spacing.


def _resize_bilinear(img: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    in_h, in_w = img.shape
    ys = np.clip((np.arange(out_h) + 0.5) * in_h / out_h - 0.5, 0, in_h - 1)
    xs = np.clip((np.arange(out_w) + 0.5) * in_w / out_w - 0.5, 0, in_w - 1)
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    y1 = np.minimum(y0 + 1, in_h - 1)
    x1 = np.minimum(x0 + 1, in_w - 1)
    wy = (ys - y0)[:, None]
    wx = (xs - x0)[None, :]
    Ia = img[np.ix_(y0, x0)]
    Ib = img[np.ix_(y0, x1)]
    Ic = img[np.ix_(y1, x0)]
    Id = img[np.ix_(y1, x1)]
    top = Ia * (1 - wx) + Ib * wx
    bot = Ic * (1 - wx) + Id * wx
    return top * (1 - wy) + bot * wy


def to_pi_luma(frame01: np.ndarray) -> np.ndarray:
    """Resize a [0,1] study frame to the Pi luminance scale (LUMA_SIZE, 0-255)."""
    g = _resize_bilinear(np.asarray(frame01, dtype=np.float64), LUMA_H, LUMA_W)
    return np.clip(g * 255.0, 0, 255).astype(np.float32)


def decision_states(sequence: np.ndarray, pipeline_config: PipelineConfig) -> list[str]:
    """Per-probe decision states for a sequence, exactly as the Pi loop derives them.

    Each consecutive pair is analysed against the immediately previous frame, and
    the active-cell set / centroid are carried forward between probes.
    """
    luma = [to_pi_luma(frame) for frame in sequence]
    states: list[str] = []
    prev = luma[0]
    prev_active: Optional[set[tuple[int, int]]] = None
    prev_centroid: Optional[tuple[float, float]] = None
    for current in luma[1:]:
        decision = analyze(
            current,
            prev,
            config=pipeline_config,
            previous_active_cells=prev_active,
            previous_centroid=prev_centroid,
        )
        states.append(decision.state)
        prev_active = set(decision.active_cells)
        cx, cy = decision.features.centroid_x, decision.features.centroid_y
        if cx is not None and cy is not None:
            prev_centroid = (cx, cy)
        prev = current
    return states


def default_video_config() -> ThreeStageConfig:
    """The Mode-③ controller shape (video HIGH, classified). Intervals are
    irrelevant to whether a clip fires, so the defaults are fine."""
    return ThreeStageConfig(high_mode="video", classify=True)


def video_outputs(states: list[str], three_config: Optional[ThreeStageConfig] = None) -> list[Any]:
    controller = ThreeStageController(three_config or default_video_config())
    return [controller.step(state, i * PROBE_SEC) for i, state in enumerate(states)]


@dataclass
class SequenceResult:
    truth: str
    fired_video: bool
    reached_mid_or_video: bool
    produced_strong: bool


def run_sequence(
    name: str, truth: str, seed: int, pipeline_config: PipelineConfig, three_config: ThreeStageConfig
) -> SequenceResult:
    states = decision_states(generate_sequence(name, seed), pipeline_config)
    outs = video_outputs(states, three_config)
    return SequenceResult(
        truth=truth,
        fired_video=any(o.trigger_video for o in outs),
        reached_mid_or_video=any(o.mode in (MID, HIGH) for o in outs),
        produced_strong=STRONG_VISITATION_CANDIDATE in states,
    )


@dataclass(frozen=True)
class ScoreWeights:
    target_signal: float = 1.0
    strong_video: float = 1.0
    noise_reject: float = 0.5
    false_video: float = 4.0  # a false clip costs power/storage; penalise most.
    # Worst-case (min over target TYPES) recall. Mean target recall alone lets the
    # optimiser abandon the single hardest class (e.g. low-SNR targets) for free;
    # rewarding the minimum forces the policy not to give up any target type.
    worst_case_target: float = 1.0


def evaluate_by_scenario(
    pipeline_config: PipelineConfig,
    *,
    n_reps: int = 4,
    seed: int = SEED,
    three_config: Optional[ThreeStageConfig] = None,
) -> dict[str, dict[str, Any]]:
    """Per-scenario outcome counts for one Pi config (the basis for composition-
    robust selection). Deterministic: seed = ``seed + scenario_index*1000 + rep``."""
    tc = three_config or default_video_config()
    out: dict[str, dict[str, Any]] = {}
    for scenario_index, (name, truth) in enumerate(SCENARIOS.items()):
        fired = signal = strong = strong_fired = 0
        for rep in range(n_reps):
            res = run_sequence(name, truth, seed + scenario_index * 1000 + rep, pipeline_config, tc)
            fired += int(res.fired_video)
            signal += int(res.reached_mid_or_video)
            if res.produced_strong:
                strong += 1
                strong_fired += int(res.fired_video)
        out[name] = {"truth": truth, "n": n_reps, "fired": fired,
                     "signal": signal, "strong": strong, "strong_fired": strong_fired}
    return out


def metrics_over(per_scenario: dict[str, dict[str, Any]], names: list[str],
                 weights: Optional[ScoreWeights] = None) -> dict[str, float]:
    """Aggregate the Mode-③ metrics + combined score over a SUBSET of scenarios.
    Used both for the full-set score and for leave-one-out robustness folds."""
    weights = weights or ScoreWeights()
    noise_total = noise_fired = target_total = target_signal = strong_seqs = strong_fired = 0
    per_type: dict[str, float] = {}
    for name in names:
        x = per_scenario[name]
        if x["truth"] == "noise":
            noise_total += x["n"]
            noise_fired += x["fired"]
        else:
            target_total += x["n"]
            target_signal += x["signal"]
            per_type[name] = x["signal"] / x["n"]
        strong_seqs += x["strong"]
        strong_fired += x["strong_fired"]
    noise_no_video_rate = 1.0 - noise_fired / noise_total if noise_total else 0.0
    false_video_trigger_rate = noise_fired / noise_total if noise_total else 0.0
    target_mid_or_video_rate = target_signal / target_total if target_total else 0.0
    strong_to_video_rate = strong_fired / strong_seqs if strong_seqs else 0.0
    worst_case_target_recall = min(per_type.values()) if per_type else 0.0
    score = (
        weights.target_signal * target_mid_or_video_rate
        + weights.worst_case_target * worst_case_target_recall
        + weights.strong_video * strong_to_video_rate
        + weights.noise_reject * noise_no_video_rate
        - weights.false_video * false_video_trigger_rate
    )
    return {
        "noise_no_video_rate": noise_no_video_rate,
        "target_mid_or_video_rate": target_mid_or_video_rate,
        "worst_case_target_recall": worst_case_target_recall,
        "strong_to_video_rate": strong_to_video_rate,
        "false_video_trigger_rate": false_video_trigger_rate,
        "score": score,
    }


def evaluate_config(
    pipeline_config: PipelineConfig,
    *,
    n_reps: int = 4,
    seed: int = SEED,
    three_config: Optional[ThreeStageConfig] = None,
    weights: Optional[ScoreWeights] = None,
) -> dict[str, float]:
    """The Mode-③ video metrics + a combined score for one Pi config (full set)."""
    per = evaluate_by_scenario(pipeline_config, n_reps=n_reps, seed=seed, three_config=three_config)
    return metrics_over(per, list(SCENARIOS), weights)


@dataclass(frozen=True)
class SearchGrid:
    """Search space — ONLY Pi-loadable FeatureConfig / ClassifierConfig values."""

    # Includes lower pixel_difference / active_cell_threshold so the search can
    # recover faint (low-SNR) targets the previous grid could not represent.
    pixel_difference: tuple[int, ...] = (15, 18, 20, 25, 30)
    active_cell_threshold: tuple[float, ...] = (0.04, 0.06, 0.10)
    strong_spatial_concentration: tuple[float, ...] = (0.60, 0.75)
    shake_shift_px: tuple[float, ...] = (2.5, 3.5)

    def iter_configs(self) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
        for pd, act, ss, sh in product(
            self.pixel_difference,
            self.active_cell_threshold,
            self.strong_spatial_concentration,
            self.shake_shift_px,
        ):
            yield (
                {"pixel_difference": pd, "active_cell_threshold": act},
                {"strong_spatial_concentration": ss, "shake_shift_px": sh},
            )


def search(
    grid: Optional[SearchGrid] = None, *, n_reps: int = 4, seed: int = SEED
) -> tuple[PipelineConfig, dict[str, float], list[dict[str, Any]]]:
    """Sweep the grid; return (best_config, best_metrics, all_rows). Deterministic."""
    grid = grid or SearchGrid()
    base = PipelineConfig()
    rows: list[dict[str, Any]] = []
    best: Optional[tuple[PipelineConfig, dict[str, float]]] = None
    for feature_kwargs, classifier_kwargs in grid.iter_configs():
        cfg = PipelineConfig(
            features=replace(base.features, **feature_kwargs),
            classifier=replace(base.classifier, **classifier_kwargs),
        )
        metrics = evaluate_config(cfg, n_reps=n_reps, seed=seed)
        rows.append({**feature_kwargs, **classifier_kwargs, **metrics})
        if best is None or metrics["score"] > best[1]["score"]:
            best = (cfg, metrics)
    assert best is not None
    return best[0], best[1], rows


def search_robust(
    grid: Optional[SearchGrid] = None, *, n_reps: int = 4, seed: int = SEED,
    weights: Optional[ScoreWeights] = None,
) -> tuple[PipelineConfig, dict[str, float], list[dict[str, Any]]]:
    """Composition-robust selection: pick the config with the highest WORST
    leave-one-scenario-out fold score, not just the best full-set mean.

    A single fixed scenario set makes the selection composition-sensitive (the
    chosen config can flip if the mix is reweighted). Maximising the worst fold
    yields a policy that stays good no matter which single scenario is emphasised;
    each row also carries ``worst_fold_score`` for the reported robustness margin.
    """
    grid = grid or SearchGrid()
    weights = weights or ScoreWeights()
    base = PipelineConfig()
    names = list(SCENARIOS)
    rows: list[dict[str, Any]] = []
    best: Optional[tuple[PipelineConfig, dict[str, float], float]] = None
    for feature_kwargs, classifier_kwargs in grid.iter_configs():
        cfg = PipelineConfig(
            features=replace(base.features, **feature_kwargs),
            classifier=replace(base.classifier, **classifier_kwargs),
        )
        per = evaluate_by_scenario(cfg, n_reps=n_reps, seed=seed)
        full = metrics_over(per, names, weights)
        worst_fold = min(
            metrics_over(per, [n for n in names if n != held_out], weights)["score"]
            for held_out in names
        )
        rows.append({**feature_kwargs, **classifier_kwargs, **full, "worst_fold_score": worst_fold})
        if best is None or worst_fold > best[2]:
            best = (cfg, {**full, "worst_fold_score": worst_fold}, worst_fold)
    assert best is not None
    return best[0], best[1], rows


def _notes(metrics: dict[str, float], n_reps: int) -> str:
    return (
        "Mode-3 runtime bridge: R5 synthetic sequences -> pipeline.analyze per frame "
        f"pair -> ThreeStageController video mode (no R6 rolling background). Rendered at "
        f"{LUMA_W}x{LUMA_H} 0-255 as a proxy for the Pi lores stream; {n_reps} reps/scenario. "
        f"Selected metrics: noise_no_video={metrics['noise_no_video_rate']:.3f}, "
        f"target_mid_or_video={metrics['target_mid_or_video_rate']:.3f}, "
        f"strong_to_video={metrics['strong_to_video_rate']:.3f}, "
        f"false_video_trigger={metrics['false_video_trigger_rate']:.3f}. Synthetic only; "
        "run Pi shadow mode on real fixed-interval frames before enabling Mode 3 in the field."
    )


def generate_policy(
    output: str | Path,
    *,
    seed: int = SEED,
    n_reps: int = 4,
    grid: Optional[SearchGrid] = None,
    policy_name: str = "mode3_runtime_bridge_v1",
    policy_version: str = "1",
) -> tuple[Path, PipelineConfig, dict[str, float]]:
    """Run the search and write the official Mode-3 runtime policy artifact
    (``mode3_runtime_bridge_policy_v1.json``). This bridge is the SOLE official
    policy-export path for the Pi runtime; the legacy pairwise search in
    ``simulation/run.py`` emits a separate, clearly-named exploratory artifact."""
    config, metrics, _rows = search(grid, n_reps=n_reps, seed=seed)
    meta = PolicyMeta(
        policy_name=policy_name,
        policy_version=policy_version,
        validation_status="simulation_informed",
        seed=seed,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        notes=_notes(metrics, n_reps),
    )
    path = write_policy(output, config, meta)
    return path, config, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Mode-3 simulation->Pi runtime bridge.")
    parser.add_argument("--output", type=Path, default=Path("mode3_runtime_bridge_policy_v1.json"))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--n-reps", type=int, default=4)
    args = parser.parse_args()
    path, _config, metrics = generate_policy(args.output, seed=args.seed, n_reps=args.n_reps)
    print(f"Wrote {path}")
    for key, value in metrics.items():
        print(f"  {key}: {value:.3f}")


if __name__ == "__main__":
    main()
