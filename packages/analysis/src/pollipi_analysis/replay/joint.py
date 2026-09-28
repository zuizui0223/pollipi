"""Joint within-run randomization test for PolliPi field validation.

This module combines multiple independently annotated PolliPi runs without ever
moving capture budget between runs. Mode 3 is replayed separately in each run,
then each Monte Carlo replicate independently randomises that run's Mode-3 still
budget over the same probe opportunities.

Primary statistic
-----------------
Micro-average event capture:
    total captured visit events / total annotated visit events

Sensitivity statistic
---------------------
Macro-average event capture:
    mean of run-level capture rates across runs that contain at least one visit

Stable per-run random seeds are derived from (master seed, replicate, run_id), so
the exact null result is invariant to manifest row ordering.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional, Union

from pollipi_analysis.policy.three_stage import ThreeStageConfig
from pollipi_analysis.replay.compare import (
    CaptureEvent,
    Probe,
    count_still_captured_visits,
    load_probe_log,
    load_visits,
    read_run_start,
    replay_classified,
    replay_random_budget,
)


@dataclass(frozen=True)
class JointRun:
    run_id: str
    probes: list[Probe]
    visits: list[tuple[float, float]]
    classified_events: list[CaptureEvent]
    low_interval_sec: float
    mid_interval_sec: float
    high_interval_sec: float

    @property
    def probe_opportunities(self) -> int:
        return len(self.probes)

    @property
    def budget_stills(self) -> int:
        return sum(1 for event in self.classified_events if event.kind == "image")

    @property
    def visits_total(self) -> int:
        return len(self.visits)

    @property
    def classified_visits_captured(self) -> int:
        return count_still_captured_visits(self.classified_events, self.visits)

    @property
    def classified_visit_capture_rate(self) -> Optional[float]:
        if not self.visits:
            return None
        return self.classified_visits_captured / len(self.visits)

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "probe_opportunities": self.probe_opportunities,
            "budget_stills": self.budget_stills,
            "visits_total": self.visits_total,
            "classified_visits_captured": self.classified_visits_captured,
            "classified_visit_capture_rate": (
                round(self.classified_visit_capture_rate, 4)
                if self.classified_visit_capture_rate is not None
                else None
            ),
            "low_interval_sec": self.low_interval_sec,
            "mid_interval_sec": self.mid_interval_sec,
            "high_interval_sec": self.high_interval_sec,
        }


@dataclass(frozen=True)
class JointRandomBudgetSummary:
    reps: int
    seed: int
    anchor_first: bool
    runs: int
    runs_with_visits: int
    total_probe_opportunities: int
    total_budget_stills: int
    total_visits: int
    classified_visits_captured: int
    classified_micro_rate: float
    random_micro_mean: float
    random_micro_q05: float
    random_micro_q50: float
    random_micro_q95: float
    micro_upper_tail_p_ge_classified: float
    classified_macro_rate: float
    random_macro_mean: float
    random_macro_q05: float
    random_macro_q50: float
    random_macro_q95: float
    macro_upper_tail_p_ge_classified: float
    run_summaries: tuple[dict, ...]

    @property
    def micro_delta_vs_random_mean(self) -> float:
        return self.classified_micro_rate - self.random_micro_mean

    @property
    def macro_delta_vs_random_mean(self) -> float:
        return self.classified_macro_rate - self.random_macro_mean

    def as_dict(self) -> dict:
        return {
            "null": "joint within-run equal-budget uniform temporal allocation",
            "primary_statistic": "micro-average event capture",
            "sensitivity_statistic": "macro-average run capture",
            "reps": self.reps,
            "seed": self.seed,
            "anchor_first": self.anchor_first,
            "runs": self.runs,
            "runs_with_visits": self.runs_with_visits,
            "total_probe_opportunities": self.total_probe_opportunities,
            "total_budget_stills": self.total_budget_stills,
            "total_visits": self.total_visits,
            "classified_visits_captured": self.classified_visits_captured,
            "classified_micro_rate": round(self.classified_micro_rate, 4),
            "random_micro_mean": round(self.random_micro_mean, 4),
            "random_micro_q05": round(self.random_micro_q05, 4),
            "random_micro_q50": round(self.random_micro_q50, 4),
            "random_micro_q95": round(self.random_micro_q95, 4),
            "micro_delta_vs_random_mean": round(self.micro_delta_vs_random_mean, 4),
            "micro_upper_tail_p_ge_classified": round(
                self.micro_upper_tail_p_ge_classified, 6
            ),
            "classified_macro_rate": round(self.classified_macro_rate, 4),
            "random_macro_mean": round(self.random_macro_mean, 4),
            "random_macro_q05": round(self.random_macro_q05, 4),
            "random_macro_q50": round(self.random_macro_q50, 4),
            "random_macro_q95": round(self.random_macro_q95, 4),
            "macro_delta_vs_random_mean": round(self.macro_delta_vs_random_mean, 4),
            "macro_upper_tail_p_ge_classified": round(
                self.macro_upper_tail_p_ge_classified, 6
            ),
            "run_summaries": list(self.run_summaries),
        }


def _optional_float(row: dict[str, str], key: str, default: float) -> float:
    raw = (row.get(key) or "").strip()
    return float(raw) if raw else default


def load_joint_manifest(
    path: Union[str, Path],
    *,
    default_config: Optional[ThreeStageConfig] = None,
) -> list[JointRun]:
    """Load a CSV manifest and replay Mode 3 separately for every run.

    Required columns:
      run_id, probe_log, visits_csv

    Optional per-run interval columns:
      low_interval_sec, mid_interval_sec, high_interval_sec

    Relative file paths are resolved against the manifest's parent directory.
    """
    manifest = Path(path)
    base_dir = manifest.resolve().parent
    default = default_config or ThreeStageConfig()
    runs: list[JointRun] = []
    seen: set[str] = set()

    with manifest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"run_id", "probe_log", "visits_csv"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "joint manifest missing required columns: " + ", ".join(sorted(missing))
            )

        for row_number, row in enumerate(reader, start=2):
            run_id = (row.get("run_id") or "").strip()
            if not run_id:
                raise ValueError(f"manifest row {row_number}: run_id is empty")
            if run_id in seen:
                raise ValueError(f"duplicate run_id in joint manifest: {run_id}")
            seen.add(run_id)

            probe_raw = (row.get("probe_log") or "").strip()
            visits_raw = (row.get("visits_csv") or "").strip()
            if not probe_raw or not visits_raw:
                raise ValueError(
                    f"manifest row {row_number}: probe_log and visits_csv are required"
                )

            probe_path = Path(probe_raw)
            visits_path = Path(visits_raw)
            if not probe_path.is_absolute():
                probe_path = base_dir / probe_path
            if not visits_path.is_absolute():
                visits_path = base_dir / visits_path

            probes = load_probe_log(probe_path)
            if not probes:
                raise ValueError(f"{run_id}: no usable probe rows in {probe_path}")
            visits = load_visits(visits_path, read_run_start(probe_path))

            low = _optional_float(row, "low_interval_sec", default.low_interval_sec)
            mid = _optional_float(row, "mid_interval_sec", default.mid_interval_sec)
            high = _optional_float(row, "high_interval_sec", default.high_interval_sec)
            cfg = replace(
                default,
                low_interval_sec=low,
                mid_interval_sec=mid,
                high_interval_sec=high,
            )
            classified = replay_classified(probes, cfg)
            runs.append(
                JointRun(
                    run_id=run_id,
                    probes=probes,
                    visits=visits,
                    classified_events=classified,
                    low_interval_sec=low,
                    mid_interval_sec=mid,
                    high_interval_sec=high,
                )
            )
    if not runs:
        raise ValueError("joint manifest contains no runs")
    return runs


def _stable_run_rng(seed: int, replicate: int, run_id: str) -> random.Random:
    token = f"{seed}\0{replicate}\0{run_id}".encode("utf-8")
    digest = hashlib.sha256(token).digest()
    return random.Random(int.from_bytes(digest[:16], "big"))


def _quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires at least one value")
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def joint_random_budget_baseline(
    runs: list[JointRun],
    *,
    reps: int = 10_000,
    seed: int = 20260928,
    anchor_first: bool = True,
) -> JointRandomBudgetSummary:
    """Joint within-run Monte Carlo test.

    The primary micro statistic weights every annotated visit equally. The macro
    sensitivity statistic weights every visit-containing run equally.
    """
    if reps <= 0:
        raise ValueError("reps must be positive")
    if not runs:
        raise ValueError("runs must be non-empty")
    ids = [run.run_id for run in runs]
    if len(set(ids)) != len(ids):
        raise ValueError("run_id values must be unique")

    with_visits = [run for run in runs if run.visits_total > 0]
    total_visits = sum(run.visits_total for run in runs)
    if total_visits <= 0:
        raise ValueError("joint test requires at least one annotated visit")

    observed_captured = sum(run.classified_visits_captured for run in runs)
    observed_micro = observed_captured / total_visits
    observed_macro = sum(
        float(run.classified_visit_capture_rate) for run in with_visits
    ) / len(with_visits)

    micro_null: list[float] = []
    macro_null: list[float] = []
    micro_ge = 0
    macro_ge = 0

    for replicate in range(reps):
        total_random_captured = 0
        run_rates: list[float] = []
        for run in runs:
            rng = _stable_run_rng(seed, replicate, run.run_id)
            random_events = replay_random_budget(
                run.probes,
                run.budget_stills,
                rng=rng,
                anchor_first=anchor_first,
            )
            captured = count_still_captured_visits(random_events, run.visits)
            total_random_captured += captured
            if run.visits_total > 0:
                run_rates.append(captured / run.visits_total)

        micro = total_random_captured / total_visits
        macro = sum(run_rates) / len(run_rates)
        micro_null.append(micro)
        macro_null.append(macro)
        if micro >= observed_micro:
            micro_ge += 1
        if macro >= observed_macro:
            macro_ge += 1

    return JointRandomBudgetSummary(
        reps=reps,
        seed=seed,
        anchor_first=anchor_first,
        runs=len(runs),
        runs_with_visits=len(with_visits),
        total_probe_opportunities=sum(run.probe_opportunities for run in runs),
        total_budget_stills=sum(run.budget_stills for run in runs),
        total_visits=total_visits,
        classified_visits_captured=observed_captured,
        classified_micro_rate=observed_micro,
        random_micro_mean=sum(micro_null) / len(micro_null),
        random_micro_q05=_quantile(micro_null, 0.05),
        random_micro_q50=_quantile(micro_null, 0.50),
        random_micro_q95=_quantile(micro_null, 0.95),
        micro_upper_tail_p_ge_classified=(1 + micro_ge) / (reps + 1),
        classified_macro_rate=observed_macro,
        random_macro_mean=sum(macro_null) / len(macro_null),
        random_macro_q05=_quantile(macro_null, 0.05),
        random_macro_q50=_quantile(macro_null, 0.50),
        random_macro_q95=_quantile(macro_null, 0.95),
        macro_upper_tail_p_ge_classified=(1 + macro_ge) / (reps + 1),
        run_summaries=tuple(run.as_dict() for run in sorted(runs, key=lambda x: x.run_id)),
    )


def format_joint_report(summary: JointRandomBudgetSummary) -> str:
    lines = [
        (
            f"Runs: {summary.runs}  visits: {summary.total_visits}  "
            f"Mode-3 stills: {summary.total_budget_stills}  "
            f"reps: {summary.reps}  seed: {summary.seed}"
        ),
        f"anchor_first={summary.anchor_first}",
        "",
        "Primary: micro-average event capture",
        (
            f"  classified={summary.classified_micro_rate*100:.1f}%  "
            f"random mean={summary.random_micro_mean*100:.1f}%  "
            f"delta={summary.micro_delta_vs_random_mean*100:+.1f} pp"
        ),
        (
            f"  random q05/q50/q95="
            f"{summary.random_micro_q05*100:.1f}%/"
            f"{summary.random_micro_q50*100:.1f}%/"
            f"{summary.random_micro_q95*100:.1f}%  "
            f"upper-tail p={summary.micro_upper_tail_p_ge_classified:.4f}"
        ),
        "",
        "Sensitivity: macro-average run capture",
        (
            f"  classified={summary.classified_macro_rate*100:.1f}%  "
            f"random mean={summary.random_macro_mean*100:.1f}%  "
            f"delta={summary.macro_delta_vs_random_mean*100:+.1f} pp"
        ),
        (
            f"  random q05/q50/q95="
            f"{summary.random_macro_q05*100:.1f}%/"
            f"{summary.random_macro_q50*100:.1f}%/"
            f"{summary.random_macro_q95*100:.1f}%  "
            f"upper-tail p={summary.macro_upper_tail_p_ge_classified:.4f}"
        ),
        "",
        "Per-run observed Mode-3 replay:",
        f"{'run_id':<24}{'probes':>8}{'stills':>8}{'visits':>8}{'captured':>10}{'rate':>9}",
        "-" * 67,
    ]
    for row in summary.run_summaries:
        rate = row["classified_visit_capture_rate"]
        rate_text = "-" if rate is None else f"{rate*100:.1f}%"
        lines.append(
            f"{row['run_id']:<24}{row['probe_opportunities']:>8}"
            f"{row['budget_stills']:>8}{row['visits_total']:>8}"
            f"{row['classified_visits_captured']:>10}{rate_text:>9}"
        )
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Joint within-run equal-budget randomization test for PolliPi Mode 3."
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="CSV: run_id,probe_log,visits_csv plus optional low/mid/high_interval_sec",
    )
    parser.add_argument("--random-reps", type=int, default=10_000)
    parser.add_argument("--random-seed", type=int, default=20260928)
    parser.add_argument(
        "--random-free-first",
        action="store_true",
        help="sensitivity analysis: randomise each run's first capture too",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args(argv)

    runs = load_joint_manifest(args.manifest)
    summary = joint_random_budget_baseline(
        runs,
        reps=args.random_reps,
        seed=args.random_seed,
        anchor_first=not args.random_free_first,
    )
    if args.json:
        print(json.dumps(summary.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_joint_report(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
