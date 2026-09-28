"""Frozen paper-level PolliPi field-validation analysis.

Combines the three still-image policies over the same independently annotated
runs and adds the already-frozen equal-budget random temporal-allocation null.

Primary questions
-----------------
H1: Mode 3 classified adaptive has higher event-level visit capture than Mode 1
    fixed timelapse.

H2: Mode 3 is non-inferior to Mode 2 motion-reactive for event capture while
    reducing non-visit still-capture burden.

RANDOM: Mode 3 event capture exceeds the within-run equal-budget random temporal
        allocation null.

Inference
---------
- unit of resampling: run (cluster bootstrap);
- bootstrap reps: 10,000 by default;
- seed: 20260928 by default;
- H2 non-inferiority margin: 0.05 absolute capture-rate units (5 percentage points);
- H1 support requires the 95% bootstrap CI lower bound for (Mode3 - Mode1) > 0;
- H2 capture non-inferiority requires the 95% CI lower bound for
  (Mode3 - Mode2) > -0.05;
- H2 cost reduction requires the 95% CI upper bound for
  (Mode3 - Mode2) non-visit stills/hour < 0;
- random timing support requires the frozen one-sided Monte Carlo p < 0.05 and
  a positive Mode3-minus-random mean effect.

The analysis is deterministic for a fixed manifest, seed and number of replicates.
Manifest order cannot change the result because runs are sorted by run_id before
bootstrap and the joint random null has run-stable RNG streams.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from pollipi_analysis.policy.three_stage import ThreeStageConfig
from pollipi_analysis.replay.compare import (
    CaptureEvent,
    count_still_captured_visits,
    replay_any_motion,
    replay_fixed,
)
from pollipi_analysis.replay.joint import (
    JointRandomBudgetSummary,
    JointRun,
    joint_random_budget_baseline,
    load_joint_manifest,
)
from pollipi_analysis.replay.preflight import preflight_field_inputs

ALPHA = 0.05
DEFAULT_NONINFERIORITY_MARGIN = 0.05
DEFAULT_BOOTSTRAP_REPS = 10_000
DEFAULT_BOOTSTRAP_SEED = 20260928
MIN_INDEPENDENT_VISIT_RUNS = 5
MIN_INDEPENDENT_COST_RUNS = 5


@dataclass(frozen=True)
class RunPolicyMetrics:
    run_id: str
    policy: str
    duration_hours: float
    stills: int
    visit_overlapping_stills: int
    nonvisit_stills: int
    visits_total: int
    visits_captured: int

    @property
    def visit_capture_rate(self) -> Optional[float]:
        if self.visits_total <= 0:
            return None
        return self.visits_captured / self.visits_total

    @property
    def visit_overlapping_stills_per_visit(self) -> Optional[float]:
        if self.visits_total <= 0:
            return None
        return self.visit_overlapping_stills / self.visits_total

    @property
    def nonvisit_stills_per_hour(self) -> Optional[float]:
        if self.duration_hours <= 0:
            return None
        return self.nonvisit_stills / self.duration_hours


@dataclass(frozen=True)
class PolicyAggregate:
    policy: str
    runs: int
    total_hours: float
    stills: int
    visit_overlapping_stills: int
    nonvisit_stills: int
    visits_total: int
    visits_captured: int

    @property
    def visit_capture_rate(self) -> float:
        return self.visits_captured / self.visits_total if self.visits_total else 0.0

    @property
    def visit_overlapping_stills_per_visit(self) -> float:
        return self.visit_overlapping_stills / self.visits_total if self.visits_total else 0.0

    @property
    def stills_per_hour(self) -> float:
        return self.stills / self.total_hours if self.total_hours > 0 else 0.0

    @property
    def nonvisit_stills_per_hour(self) -> float:
        return self.nonvisit_stills / self.total_hours if self.total_hours > 0 else 0.0

    def as_dict(self) -> dict:
        return {
            "policy": self.policy,
            "runs": self.runs,
            "total_hours": round(self.total_hours, 4),
            "stills": self.stills,
            "stills_per_hour": round(self.stills_per_hour, 4),
            "visits_total": self.visits_total,
            "visits_captured": self.visits_captured,
            "visit_capture_rate": round(self.visit_capture_rate, 4),
            "visit_overlapping_stills": self.visit_overlapping_stills,
            "visit_overlapping_stills_per_visit": round(
                self.visit_overlapping_stills_per_visit, 4
            ),
            "nonvisit_stills": self.nonvisit_stills,
            "nonvisit_stills_per_hour": round(self.nonvisit_stills_per_hour, 4),
        }


@dataclass(frozen=True)
class BootstrapInterval:
    observed: float
    lower: float
    upper: float
    reps: int
    seed: int

    def as_dict(self) -> dict:
        return {
            "observed": round(self.observed, 6),
            "lower_95": round(self.lower, 6),
            "upper_95": round(self.upper, 6),
            "reps": self.reps,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class FieldValidationSummary:
    alpha: float
    noninferiority_margin: float
    bootstrap_reps: int
    bootstrap_seed: int
    policies: tuple[PolicyAggregate, ...]
    h1_capture_difference: BootstrapInterval
    h2_capture_difference: BootstrapInterval
    h2_nonvisit_stills_per_hour_difference: BootstrapInterval
    random_budget: JointRandomBudgetSummary
    visit_run_count: int
    cost_run_count: int
    visit_inference_eligible: bool
    cost_inference_eligible: bool
    primary_inference_eligible: bool
    eligibility_reasons: tuple[str, ...]
    h1_supported: bool
    h2_capture_noninferior: bool
    h2_cost_reduction_supported: bool
    h2_supported: bool
    random_timing_supported: bool
    all_primary_criteria_supported: bool
    run_metrics: tuple[RunPolicyMetrics, ...]

    def as_dict(self) -> dict:
        return {
            "analysis_contract": "pollipi-field-validation-v1",
            "alpha": self.alpha,
            "noninferiority_margin": self.noninferiority_margin,
            "bootstrap_reps": self.bootstrap_reps,
            "bootstrap_seed": self.bootstrap_seed,
            "policies": [p.as_dict() for p in self.policies],
            "h1_mode3_minus_fixed_capture": self.h1_capture_difference.as_dict(),
            "h2_mode3_minus_motion_capture": self.h2_capture_difference.as_dict(),
            "h2_mode3_minus_motion_nonvisit_stills_per_hour": (
                self.h2_nonvisit_stills_per_hour_difference.as_dict()
            ),
            "random_budget_null": self.random_budget.as_dict(),
            "evidence_eligibility": {
                "minimum_independent_visit_runs": MIN_INDEPENDENT_VISIT_RUNS,
                "minimum_independent_cost_runs": MIN_INDEPENDENT_COST_RUNS,
                "visit_run_count": self.visit_run_count,
                "cost_run_count": self.cost_run_count,
                "visit_inference_eligible": self.visit_inference_eligible,
                "cost_inference_eligible": self.cost_inference_eligible,
                "primary_inference_eligible": self.primary_inference_eligible,
                "reasons": list(self.eligibility_reasons),
            },
            "claim_gates": {
                "h1_supported": self.h1_supported,
                "h2_capture_noninferior": self.h2_capture_noninferior,
                "h2_cost_reduction_supported": self.h2_cost_reduction_supported,
                "h2_supported": self.h2_supported,
                "random_timing_supported": self.random_timing_supported,
                "all_primary_criteria_supported": self.all_primary_criteria_supported,
            },
            "run_metrics": [
                {
                    "run_id": r.run_id,
                    "policy": r.policy,
                    "duration_hours": round(r.duration_hours, 4),
                    "stills": r.stills,
                    "visit_overlapping_stills": r.visit_overlapping_stills,
                    "nonvisit_stills": r.nonvisit_stills,
                    "visits_total": r.visits_total,
                    "visits_captured": r.visits_captured,
                    "visit_capture_rate": (
                        round(r.visit_capture_rate, 4)
                        if r.visit_capture_rate is not None
                        else None
                    ),
                    "visit_overlapping_stills_per_visit": (
                        round(r.visit_overlapping_stills_per_visit, 4)
                        if r.visit_overlapping_stills_per_visit is not None
                        else None
                    ),
                    "nonvisit_stills_per_hour": (
                        round(r.nonvisit_stills_per_hour, 4)
                        if r.nonvisit_stills_per_hour is not None
                        else None
                    ),
                }
                for r in self.run_metrics
            ],
        }


def _capture_overlaps_any_visit(time_sec: float, visits: list[tuple[float, float]]) -> bool:
    return any(start <= time_sec <= end for start, end in visits)


def _run_policy_metrics(
    run: JointRun, policy: str, events: list[CaptureEvent]
) -> RunPolicyMetrics:
    still_times = [event.time_sec for event in events if event.kind == "image"]
    visit_overlapping = sum(
        1 for time_sec in still_times if _capture_overlaps_any_visit(time_sec, run.visits)
    )
    duration_sec = (
        run.probes[-1].elapsed_sec - run.probes[0].elapsed_sec
        if len(run.probes) >= 2
        else 0.0
    )
    return RunPolicyMetrics(
        run_id=run.run_id,
        policy=policy,
        duration_hours=duration_sec / 3600.0,
        stills=len(still_times),
        visit_overlapping_stills=visit_overlapping,
        nonvisit_stills=len(still_times) - visit_overlapping,
        visits_total=run.visits_total,
        visits_captured=count_still_captured_visits(events, run.visits),
    )


def _policy_metrics_for_runs(runs: list[JointRun]) -> list[RunPolicyMetrics]:
    rows: list[RunPolicyMetrics] = []
    for run in sorted(runs, key=lambda x: x.run_id):
        cfg = ThreeStageConfig(
            low_interval_sec=run.low_interval_sec,
            mid_interval_sec=run.mid_interval_sec,
            high_interval_sec=run.high_interval_sec,
        )
        rows.append(
            _run_policy_metrics(
                run,
                "1 fixed",
                replay_fixed(run.probes, run.low_interval_sec),
            )
        )
        rows.append(
            _run_policy_metrics(
                run,
                "2 any-motion",
                replay_any_motion(run.probes, cfg),
            )
        )
        rows.append(
            _run_policy_metrics(
                run,
                "3 classified",
                run.classified_events,
            )
        )
    return rows


def _aggregate(rows: Iterable[RunPolicyMetrics], policy: str) -> PolicyAggregate:
    selected = [row for row in rows if row.policy == policy]
    return PolicyAggregate(
        policy=policy,
        runs=len(selected),
        total_hours=sum(row.duration_hours for row in selected),
        stills=sum(row.stills for row in selected),
        visit_overlapping_stills=sum(row.visit_overlapping_stills for row in selected),
        nonvisit_stills=sum(row.nonvisit_stills for row in selected),
        visits_total=sum(row.visits_total for row in selected),
        visits_captured=sum(row.visits_captured for row in selected),
    )


def _quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires values")
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def _capture_difference_for_sample(
    sample_run_ids: list[str],
    by_run_policy: dict[tuple[str, str], RunPolicyMetrics],
    a: str,
    b: str,
) -> float:
    total_visits = 0
    captured_a = 0
    captured_b = 0
    for run_id in sample_run_ids:
        ra = by_run_policy[(run_id, a)]
        rb = by_run_policy[(run_id, b)]
        total_visits += ra.visits_total
        captured_a += ra.visits_captured
        captured_b += rb.visits_captured
    if total_visits <= 0:
        raise ValueError("capture bootstrap sample contains no visits")
    return captured_a / total_visits - captured_b / total_visits


def _nonvisit_rate_difference_for_sample(
    sample_run_ids: list[str],
    by_run_policy: dict[tuple[str, str], RunPolicyMetrics],
    a: str,
    b: str,
) -> float:
    hours = 0.0
    nonvisit_a = 0
    nonvisit_b = 0
    for run_id in sample_run_ids:
        ra = by_run_policy[(run_id, a)]
        rb = by_run_policy[(run_id, b)]
        hours += ra.duration_hours
        nonvisit_a += ra.nonvisit_stills
        nonvisit_b += rb.nonvisit_stills
    if hours <= 0:
        raise ValueError("cost bootstrap sample has zero duration")
    return nonvisit_a / hours - nonvisit_b / hours


def _cluster_bootstrap_interval(
    observed: float,
    *,
    run_ids: list[str],
    statistic,
    reps: int,
    seed: int,
) -> BootstrapInterval:
    if reps <= 0:
        raise ValueError("bootstrap reps must be positive")
    if not run_ids:
        raise ValueError("bootstrap requires at least one run")
    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(reps):
        sampled = [rng.choice(run_ids) for _ in run_ids]
        values.append(statistic(sampled))
    return BootstrapInterval(
        observed=observed,
        lower=_quantile(values, 0.025),
        upper=_quantile(values, 0.975),
        reps=reps,
        seed=seed,
    )


def analyze_field_validation(
    runs: list[JointRun],
    *,
    bootstrap_reps: int = DEFAULT_BOOTSTRAP_REPS,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    noninferiority_margin: float = DEFAULT_NONINFERIORITY_MARGIN,
    random_reps: int = 10_000,
    random_seed: int = 20260928,
    random_anchor_first: bool = True,
    alpha: float = ALPHA,
) -> FieldValidationSummary:
    """Run the complete frozen field-validation analysis."""
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between 0 and 1")
    if noninferiority_margin < 0:
        raise ValueError("noninferiority margin must be non-negative")
    if not runs:
        raise ValueError("runs must be non-empty")

    metrics = _policy_metrics_for_runs(runs)
    by_run_policy = {(r.run_id, r.policy): r for r in metrics}
    visit_run_ids = sorted(
        {
            r.run_id
            for r in metrics
            if r.policy == "3 classified" and r.visits_total > 0
        }
    )
    cost_run_ids = sorted(
        {
            r.run_id
            for r in metrics
            if r.policy == "3 classified" and r.duration_hours > 0
        }
    )
    if not visit_run_ids:
        raise ValueError("field validation requires at least one run with annotated visits")
    if not cost_run_ids:
        raise ValueError("field validation requires at least one positive-duration run")

    fixed = _aggregate(metrics, "1 fixed")
    motion = _aggregate(metrics, "2 any-motion")
    classified = _aggregate(metrics, "3 classified")

    h1_observed = classified.visit_capture_rate - fixed.visit_capture_rate
    h2_observed = classified.visit_capture_rate - motion.visit_capture_rate
    h2_cost_observed = (
        classified.nonvisit_stills_per_hour - motion.nonvisit_stills_per_hour
    )

    h1_ci = _cluster_bootstrap_interval(
        h1_observed,
        run_ids=visit_run_ids,
        statistic=lambda sample: _capture_difference_for_sample(
            sample, by_run_policy, "3 classified", "1 fixed"
        ),
        reps=bootstrap_reps,
        seed=bootstrap_seed + 101,
    )
    h2_ci = _cluster_bootstrap_interval(
        h2_observed,
        run_ids=visit_run_ids,
        statistic=lambda sample: _capture_difference_for_sample(
            sample, by_run_policy, "3 classified", "2 any-motion"
        ),
        reps=bootstrap_reps,
        seed=bootstrap_seed + 202,
    )
    h2_cost_ci = _cluster_bootstrap_interval(
        h2_cost_observed,
        run_ids=cost_run_ids,
        statistic=lambda sample: _nonvisit_rate_difference_for_sample(
            sample, by_run_policy, "3 classified", "2 any-motion"
        ),
        reps=bootstrap_reps,
        seed=bootstrap_seed + 303,
    )

    random_summary = joint_random_budget_baseline(
        runs,
        reps=random_reps,
        seed=random_seed,
        anchor_first=random_anchor_first,
    )

    visit_run_count = len(visit_run_ids)
    cost_run_count = len(cost_run_ids)
    visit_eligible = visit_run_count >= MIN_INDEPENDENT_VISIT_RUNS
    cost_eligible = cost_run_count >= MIN_INDEPENDENT_COST_RUNS
    eligibility_reasons: list[str] = []
    if not visit_eligible:
        eligibility_reasons.append(
            f"visit inference requires at least {MIN_INDEPENDENT_VISIT_RUNS} "
            f"independent visit-containing runs; observed {visit_run_count}"
        )
    if not cost_eligible:
        eligibility_reasons.append(
            f"cost inference requires at least {MIN_INDEPENDENT_COST_RUNS} "
            f"positive-duration runs; observed {cost_run_count}"
        )
    primary_eligible = visit_eligible and cost_eligible

    h1_supported = visit_eligible and h1_ci.lower > 0.0
    h2_noninferior = visit_eligible and h2_ci.lower > -noninferiority_margin
    h2_cost_supported = cost_eligible and h2_cost_ci.upper < 0.0
    h2_supported = h2_noninferior and h2_cost_supported
    random_supported = (
        visit_eligible
        and random_summary.micro_delta_vs_random_mean > 0.0
        and random_summary.micro_upper_tail_p_ge_classified < alpha
    )
    all_supported = primary_eligible and h1_supported and h2_supported and random_supported

    return FieldValidationSummary(
        alpha=alpha,
        noninferiority_margin=noninferiority_margin,
        bootstrap_reps=bootstrap_reps,
        bootstrap_seed=bootstrap_seed,
        policies=(fixed, motion, classified),
        h1_capture_difference=h1_ci,
        h2_capture_difference=h2_ci,
        h2_nonvisit_stills_per_hour_difference=h2_cost_ci,
        random_budget=random_summary,
        visit_run_count=visit_run_count,
        cost_run_count=cost_run_count,
        visit_inference_eligible=visit_eligible,
        cost_inference_eligible=cost_eligible,
        primary_inference_eligible=primary_eligible,
        eligibility_reasons=tuple(eligibility_reasons),
        h1_supported=h1_supported,
        h2_capture_noninferior=h2_noninferior,
        h2_cost_reduction_supported=h2_cost_supported,
        h2_supported=h2_supported,
        random_timing_supported=random_supported,
        all_primary_criteria_supported=all_supported,
        run_metrics=tuple(metrics),
    )


def format_field_validation_report(summary: FieldValidationSummary) -> str:
    lines = [
        "PolliPi field validation v1",
        (
            f"runs={summary.policies[0].runs}  "
            f"visits={summary.policies[0].visits_total}  "
            f"bootstrap={summary.bootstrap_reps}  "
            f"random={summary.random_budget.reps}"
        ),
        "",
        f"{'policy':<18}{'visit%':>9}{'stills':>9}{'stills/h':>11}{'nonvisit/h':>13}{'visit imgs/visit':>17}",
        "-" * 77,
    ]
    for policy in summary.policies:
        lines.append(
            f"{policy.policy:<18}"
            f"{policy.visit_capture_rate*100:>8.1f}%"
            f"{policy.stills:>9}"
            f"{policy.stills_per_hour:>11.1f}"
            f"{policy.nonvisit_stills_per_hour:>13.1f}"
            f"{policy.visit_overlapping_stills_per_visit:>17.2f}"
        )

    h1 = summary.h1_capture_difference
    h2 = summary.h2_capture_difference
    cost = summary.h2_nonvisit_stills_per_hour_difference
    rb = summary.random_budget
    lines.extend(
        [
            "",
            (
                f"Evidence eligibility: visit_runs={summary.visit_run_count}/"
                f"{MIN_INDEPENDENT_VISIT_RUNS}, cost_runs={summary.cost_run_count}/"
                f"{MIN_INDEPENDENT_COST_RUNS}, "
                f"eligible={summary.primary_inference_eligible}"
            ),
            *[
                f"  INSUFFICIENT: {reason}"
                for reason in summary.eligibility_reasons
            ],
            "",
            "Frozen claim gates",
            (
                f"H1  Mode3 - fixed visit capture: {h1.observed*100:+.1f} pp "
                f"[95% CI {h1.lower*100:+.1f}, {h1.upper*100:+.1f}] pp  "
                f"supported={summary.h1_supported}"
            ),
            (
                f"H2a Mode3 - motion visit capture: {h2.observed*100:+.1f} pp "
                f"[95% CI {h2.lower*100:+.1f}, {h2.upper*100:+.1f}] pp  "
                f"margin=-{summary.noninferiority_margin*100:.1f} pp  "
                f"noninferior={summary.h2_capture_noninferior}"
            ),
            (
                f"H2b Mode3 - motion nonvisit stills/h: {cost.observed:+.2f} "
                f"[95% CI {cost.lower:+.2f}, {cost.upper:+.2f}]  "
                f"reduction={summary.h2_cost_reduction_supported}"
            ),
            (
                f"Random equal-budget: Mode3={rb.classified_micro_rate*100:.1f}% "
                f"random mean={rb.random_micro_mean*100:.1f}% "
                f"delta={rb.micro_delta_vs_random_mean*100:+.1f} pp "
                f"p={rb.micro_upper_tail_p_ge_classified:.4f}  "
                f"supported={summary.random_timing_supported}"
            ),
            "",
            f"ALL PRIMARY CRITERIA SUPPORTED: {summary.all_primary_criteria_supported}",
        ]
    )
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen PolliPi field-validation analysis."
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="joint manifest: run_id,probe_log,visits_csv plus optional intervals",
    )
    parser.add_argument("--bootstrap-reps", type=int, default=DEFAULT_BOOTSTRAP_REPS)
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    parser.add_argument(
        "--noninferiority-margin",
        type=float,
        default=DEFAULT_NONINFERIORITY_MARGIN,
        help="absolute Mode3-vs-motion visit-capture margin (default 0.05)",
    )
    parser.add_argument("--random-reps", type=int, default=10_000)
    parser.add_argument("--random-seed", type=int, default=20260928)
    parser.add_argument("--random-free-first", action="store_true")
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="also write the complete versioned result JSON",
    )
    args = parser.parse_args(argv)

    preflight = preflight_field_inputs(args.manifest)
    if not preflight.ok:
        if args.output_json is not None:
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            args.output_json.write_text(
                json.dumps(
                    {
                        "analysis_contract": "pollipi-field-validation-v1",
                        "status": "input_preflight_failed",
                        "input_preflight": preflight.as_dict(),
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
        for error in preflight.errors:
            print(f"INPUT ERROR: {error}")
        return 2

    runs = load_joint_manifest(args.manifest)
    summary = analyze_field_validation(
        runs,
        bootstrap_reps=args.bootstrap_reps,
        bootstrap_seed=args.bootstrap_seed,
        noninferiority_margin=args.noninferiority_margin,
        random_reps=args.random_reps,
        random_seed=args.random_seed,
        random_anchor_first=not args.random_free_first,
    )
    payload = summary.as_dict()
    payload["input_preflight"] = preflight.as_dict()
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(format_field_validation_report(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
