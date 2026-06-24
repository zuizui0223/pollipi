"""Select a Pi policy by power-aware timeline cost (Phase 2).

Unlike ``simulation.search`` (per-scenario detection accuracy / cost), this
evaluates each candidate ``PipelineConfig`` by simulating the real capture
timeline under the two-stage LOW/HIGH controller and scoring energy, false-HIGH
rate, and insect coverage. The selected policy is the one that is cheapest to run
while still going HIGH for genuine insect activity — exactly the device's goal.

Deterministic for a fixed seed. Emits plain dict rows suitable for CSV.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from pollipi_analysis.features.compute import FeatureConfig
from pollipi_analysis.pipeline import ClassifierConfig, PipelineConfig
from pollipi_analysis.policy.two_stage import TwoStageConfig
from pollipi_analysis.simulation.timeline import (
    PowerObjectiveWeights,
    TimelineSegment,
    generate_timeline,
    power_cost,
    simulate_power,
)


@dataclass(frozen=True)
class PowerSearchGrid:
    cell_sizes: tuple[int, ...] = (24, 32, 48)
    pixel_differences: tuple[int, ...] = (20, 25, 30)
    strong_spatial: tuple[float, ...] = (0.55, 0.70, 0.85)


def default_timelines(seed: int = 7) -> list[tuple[list, list[bool]]]:
    """Representative timelines mixing quiet/wind/shadow/sway with insect windows.

    Each timeline is long enough that the steady-state LOW draw dominates energy,
    with a couple of bounded insect traverses that a good policy should cover at
    HIGH and the noise stretches it should not.
    """
    layouts = [
        [
            TimelineSegment("quiet", 12),
            TimelineSegment("broad_wind", 10),
            TimelineSegment("insect", 8),
            TimelineSegment("quiet", 10),
            TimelineSegment("moving_shadow", 10),
            TimelineSegment("insect", 8),
            TimelineSegment("local_sway", 10),
            TimelineSegment("quiet", 12),
        ],
        [
            TimelineSegment("quiet", 16),
            TimelineSegment("local_sway", 12),
            TimelineSegment("insect", 8),
            TimelineSegment("broad_wind", 12),
            TimelineSegment("quiet", 16),
        ],
    ]
    return [generate_timeline(layout, seed=seed + i) for i, layout in enumerate(layouts)]


def evaluate_power_policy(
    pipeline_config: PipelineConfig,
    *,
    controller_config: TwoStageConfig,
    timelines: Iterable[tuple[list, list[bool]]],
    base_rate_sec: float,
    weights: Optional[PowerObjectiveWeights] = None,
) -> dict[str, Any]:
    """Aggregate power metrics + total cost for one policy over several timelines."""
    weights = weights or PowerObjectiveWeights()
    total_cost = 0.0
    cap_per_hour = 0.0
    false_high = 0.0
    coverage = 0.0
    n = 0
    for frames, truth in timelines:
        metrics = simulate_power(
            frames,
            truth,
            base_rate_sec=base_rate_sec,
            controller_config=controller_config,
            pipeline_config=pipeline_config,
        )
        total_cost += power_cost(metrics, weights)
        cap_per_hour += metrics.captures_per_hour
        false_high += metrics.false_high_rate
        coverage += metrics.coverage
        n += 1
    n = max(1, n)
    return {
        "cost": total_cost / n,
        "captures_per_hour": cap_per_hour / n,
        "false_high_rate": false_high / n,
        "coverage": coverage / n,
    }


def run_power_search(
    grid: Optional[PowerSearchGrid] = None,
    *,
    controller_config: Optional[TwoStageConfig] = None,
    seed: int = 7,
    weights: Optional[PowerObjectiveWeights] = None,
) -> list[dict[str, Any]]:
    grid = grid or PowerSearchGrid()
    controller = controller_config or TwoStageConfig()
    timelines = default_timelines(seed)
    # The timeline base cadence is the HIGH rate (finest sampling the policy reaches).
    base_rate = controller.high_rate_sec
    results: list[dict[str, Any]] = []
    for cell_size in grid.cell_sizes:
        for pixel_difference in grid.pixel_differences:
            for strong_spatial in grid.strong_spatial:
                config = PipelineConfig(
                    features=FeatureConfig(cell_size=cell_size, pixel_difference=pixel_difference),
                    classifier=ClassifierConfig(strong_spatial_concentration=strong_spatial),
                )
                summary = evaluate_power_policy(
                    config,
                    controller_config=controller,
                    timelines=timelines,
                    base_rate_sec=base_rate,
                    weights=weights,
                )
                results.append(
                    {
                        "cell_size": cell_size,
                        "pixel_difference": pixel_difference,
                        "strong_spatial_concentration": strong_spatial,
                        **summary,
                    }
                )
    return results


def select_power_policy(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Pick the lowest power-cost config.

    Ties break toward lower false-HIGH, then higher coverage, then smaller cell
    size (cheaper to compute on the Pi).
    """
    rows = list(results)
    if not rows:
        raise ValueError("no power-search results to select from")
    return min(
        rows,
        key=lambda r: (
            round(r["cost"], 9),
            r["false_high_rate"],
            -r["coverage"],
            r["cell_size"],
        ),
    )
