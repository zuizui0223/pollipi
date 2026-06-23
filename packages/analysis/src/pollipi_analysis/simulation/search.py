"""Reproducible parameter search over the labelled scenario set.

Sweeps a small grid of feature/classifier parameters and scores each
configuration on two competing objectives (a Pareto trade-off):

- ``candidate_recall``: fraction of clean target scenarios correctly called
  ``strong_visitation_candidate``.
- ``false_trigger_rate``: fraction of pure-environment scenarios wrongly called
  ``strong_visitation_candidate`` (these cost power and storage in the field).

The search is deterministic for a fixed seed and emits plain dict rows suitable
for CSV writing.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable

from pollipi_analysis.features.compute import FeatureConfig
from pollipi_analysis.pipeline import ClassifierConfig, PipelineConfig, analyze
from pollipi_analysis.schemas.states import STRONG_VISITATION_CANDIDATE
from pollipi_analysis.simulation.scenarios import LABELED_SCENARIOS
from pollipi_analysis.simulation.synthetic import simulate_pair


@dataclass(frozen=True)
class SearchGrid:
    cell_sizes: tuple[int, ...] = (24, 32, 48)
    pixel_differences: tuple[int, ...] = (20, 25, 30)
    strong_spatial: tuple[float, ...] = (0.55, 0.70, 0.85)


@dataclass(frozen=True)
class CostWeights:
    """Field-cost weights for policy selection.

    A ``false_strong`` (environment wrongly called ``strong_visitation_candidate``)
    shortens the next interval, costing power, storage, and review burden — so it
    is penalised most heavily. A missed target loses evidence (moderate). An
    environment frame logged as ``uncertain`` is cheap (metadata only).
    """

    false_strong: float = 10.0
    target_miss: float = 3.0
    false_uncertain: float = 0.5


def evaluate_config(
    config: PipelineConfig, *, seed: int = 7, weights: CostWeights | None = None
) -> dict[str, Any]:
    weights = weights or CostWeights()
    rows = []
    correct = 0
    target_total = 0
    target_hit = 0
    env_total = 0
    env_false = 0
    cost = 0.0
    for scenario in LABELED_SCENARIOS:
        background, frame = simulate_pair(scenario.name, seed=seed)
        decision = analyze(frame, background, config=config)
        predicted = decision.state
        is_correct = predicted == scenario.expected
        correct += int(is_correct)
        if scenario.family == "target":
            target_total += 1
            if predicted == STRONG_VISITATION_CANDIDATE:
                target_hit += 1
            else:
                cost += weights.target_miss
        elif scenario.family == "environment":
            env_total += 1
            if predicted == STRONG_VISITATION_CANDIDATE:
                env_false += 1
                cost += weights.false_strong
            elif predicted == "uncertain_local_activity":
                cost += weights.false_uncertain
        rows.append(
            {
                "scenario": scenario.name,
                "family": scenario.family,
                "expected": scenario.expected,
                "predicted": predicted,
                "reason": decision.reason,
                "correct": is_correct,
            }
        )
    return {
        "accuracy": correct / max(1, len(LABELED_SCENARIOS)),
        "candidate_recall": target_hit / max(1, target_total),
        "false_trigger_rate": env_false / max(1, env_total),
        "cost": cost,
        "rows": rows,
    }


def run_search(
    grid: SearchGrid | None = None, *, seed: int = 7, weights: CostWeights | None = None
) -> list[dict[str, Any]]:
    grid = grid or SearchGrid()
    weights = weights or CostWeights()
    results: list[dict[str, Any]] = []
    for cell_size in grid.cell_sizes:
        for pixel_difference in grid.pixel_differences:
            for strong_spatial in grid.strong_spatial:
                features = FeatureConfig(cell_size=cell_size, pixel_difference=pixel_difference)
                classifier = ClassifierConfig(strong_spatial_concentration=strong_spatial)
                config = PipelineConfig(features=features, classifier=classifier)
                summary = evaluate_config(config, seed=seed, weights=weights)
                results.append(
                    {
                        "cell_size": cell_size,
                        "pixel_difference": pixel_difference,
                        "strong_spatial_concentration": strong_spatial,
                        "accuracy": summary["accuracy"],
                        "candidate_recall": summary["candidate_recall"],
                        "false_trigger_rate": summary["false_trigger_rate"],
                        "cost": summary["cost"],
                    }
                )
    return results


def select_policy(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Pick the lowest-cost configuration.

    Ties are broken by higher candidate recall, then lower false-trigger rate,
    then a smaller cell size (cheaper to compute). Returns the chosen row.
    """
    rows = list(results)
    if not rows:
        raise ValueError("no search results to select from")
    return min(
        rows,
        key=lambda r: (
            r["cost"],
            -r["candidate_recall"],
            r["false_trigger_rate"],
            r["cell_size"],
        ),
    )


def pareto_front(results: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Configs not dominated on (high recall, low false-trigger)."""
    items = list(results)
    front: list[dict[str, Any]] = []
    for a in items:
        dominated = any(
            b is not a
            and b["candidate_recall"] >= a["candidate_recall"]
            and b["false_trigger_rate"] <= a["false_trigger_rate"]
            and (
                b["candidate_recall"] > a["candidate_recall"]
                or b["false_trigger_rate"] < a["false_trigger_rate"]
            )
            for b in items
        )
        if not dominated:
            front.append(a)
    return front
