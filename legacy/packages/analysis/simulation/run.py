"""Reproducible simulation entry point: CSV + plot output.

Run with::

    python -m pollipi_analysis.simulation --seed 7 --out-dir sim_out

Outputs (deterministic for a fixed seed):

- ``scenario_decisions.csv``  : per-scenario predicted vs expected state + features
- ``parameter_search.csv``    : grid search with recall / false-trigger metrics
- ``pareto_front.csv``        : non-dominated configs
- ``shadow_<scenario>.csv``   : shadow-mode log for each temporal sequence
- ``pareto.png``              : recall vs false-trigger scatter (if matplotlib present)

Pure: no FastAPI, no Picamera2. Only writes to the chosen output directory.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Sequence

from datetime import datetime, timezone

from pollipi_analysis.features.compute import FeatureConfig
from pollipi_analysis.pipeline import ClassifierConfig, PipelineConfig, analyze
from pollipi_analysis.policy.artifact import PolicyMeta, write_policy
from pollipi_analysis.policy.state_policy import IntervalBounds
from pollipi_analysis.shadow import run_shadow_mode
from pollipi_analysis.simulation.scenarios import LABELED_SCENARIOS
from pollipi_analysis.simulation.search import pareto_front, run_search, select_policy
from pollipi_analysis.simulation.synthetic import simulate_pair, simulate_sequence

SEQUENCE_SCENARIOS = ("target_traverse", "local_sway", "moving_shadow", "broad_wind", "quiet")


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _scenario_rows(seed: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in LABELED_SCENARIOS:
        background, frame = simulate_pair(scenario.name, seed=seed)
        decision = analyze(frame, background)
        row = {
            "scenario": scenario.name,
            "family": scenario.family,
            "expected": scenario.expected,
            "predicted": decision.state,
            "reason": decision.reason,
            "correct": decision.state == scenario.expected,
        }
        row.update(decision.features.to_dict())
        rows.append(row)
    return rows


def _shadow_rows(scenario: str, seed: int) -> list[dict[str, Any]]:
    frames = simulate_sequence(scenario, n_frames=6, seed=seed)
    bounds = IntervalBounds(baseline_interval_sec=60, min_interval_sec=10, max_interval_sec=180)
    records = run_shadow_mode(frames, bounds=bounds, device_id=f"sim-{scenario}")
    return [record.to_row() for record in records]


def _maybe_plot(search_rows: Sequence[dict[str, Any]], out_dir: Path) -> str:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # pragma: no cover - plotting is optional
        return "matplotlib unavailable; skipped plot"

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(
        [r["false_trigger_rate"] for r in search_rows],
        [r["candidate_recall"] for r in search_rows],
        c="#1f77b4",
        alpha=0.6,
        label="configs",
    )
    front = pareto_front(search_rows)
    ax.scatter(
        [r["false_trigger_rate"] for r in front],
        [r["candidate_recall"] for r in front],
        c="#d62728",
        marker="x",
        s=80,
        label="pareto front",
    )
    ax.set_xlabel("false trigger rate (environment -> candidate)")
    ax.set_ylabel("candidate recall (target -> candidate)")
    ax.set_title("Mesh rule parameter search")
    ax.legend()
    fig.tight_layout()
    out_path = out_dir / "pareto.png"
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return f"wrote {out_path}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PolliPi mesh analysis simulation")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out-dir", type=Path, default=Path("sim_out"))
    args = parser.parse_args(argv)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    scenario_rows = _scenario_rows(args.seed)
    _write_csv(out_dir / "scenario_decisions.csv", scenario_rows)

    search_rows = run_search(seed=args.seed)
    _write_csv(out_dir / "parameter_search.csv", search_rows)
    _write_csv(out_dir / "pareto_front.csv", pareto_front(search_rows))

    # Phase D: select the lowest field-cost config and export a Pi-loadable policy.
    best = select_policy(search_rows)
    chosen_config = PipelineConfig(
        features=FeatureConfig(cell_size=best["cell_size"], pixel_difference=best["pixel_difference"]),
        classifier=ClassifierConfig(strong_spatial_concentration=best["strong_spatial_concentration"]),
    )
    # LEGACY/exploratory pairwise (single-frame) cost-weighted search. This is NOT the
    # official Pi runtime policy — that is exported by simulation/runtime_bridge.py as
    # mode3_runtime_bridge_policy_v1.json. Kept for scenario/exploratory history and
    # written under a distinct name so the Pi never confuses the two artifacts.
    policy_path = write_policy(
        out_dir / "legacy_pairwise_policy.json",
        chosen_config,
        PolicyMeta(
            policy_name="legacy_pairwise_v1",
            policy_version="1",
            validation_status="synthetic_only",
            seed=args.seed,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            notes="LEGACY exploratory single-frame-pair cost-weighted search; NOT the official "
            "Mode-3 runtime policy (runtime_bridge -> mode3_runtime_bridge_policy_v1.json); not field-validated",
        ),
    )

    for scenario in SEQUENCE_SCENARIOS:
        _write_csv(out_dir / f"shadow_{scenario}.csv", _shadow_rows(scenario, args.seed))

    plot_msg = _maybe_plot(search_rows, out_dir)

    correct = sum(1 for r in scenario_rows if r["correct"])
    print(f"seed={args.seed} out_dir={out_dir}")
    print(f"scenario accuracy: {correct}/{len(scenario_rows)}")
    print(f"search configs: {len(search_rows)}; pareto front: {len(pareto_front(search_rows))}")
    print(f"selected policy cost={best['cost']:.2f} recall={best['candidate_recall']:.2f} "
          f"false_trigger={best['false_trigger_rate']:.2f} -> {policy_path}")
    print(plot_msg)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
