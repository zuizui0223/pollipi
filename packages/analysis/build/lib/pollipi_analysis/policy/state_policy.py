"""State-driven adaptive-interval policy (Issue #14 active design).

Maps a three-state mesh decision to the interval that *would* be used for the
next scheduled capture. This is the policy logged in shadow mode; it does NOT
enable live adaptive control on its own.

Policy table:

    environmental_noise         -> retain baseline, or cautiously lengthen
    no_activity                 -> move gradually toward the maximum interval
    uncertain_local_activity    -> retain baseline interval (log metadata only)
    strong_visitation_candidate -> shorten ONLY the next scheduled interval

The function is intentionally stateless: it computes the next interval from the
fixed baseline/min/max and the current interval, so a shadow log can record
exactly what would have happened at each capture. The transient nature of a
strong candidate (shorten only the next interval) is preserved by the caller
keeping ``baseline_interval_sec`` fixed: the policy never mutates the baseline.
"""
from __future__ import annotations

from dataclasses import dataclass

from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
    DecisionState,
)


@dataclass(frozen=True)
class IntervalPlan:
    next_interval_sec: float
    activity_score: float
    reason: str
    # True only for strong_visitation_candidate: the shortened interval applies
    # to the next capture only; the baseline is unchanged.
    transient: bool = False


@dataclass(frozen=True)
class IntervalBounds:
    baseline_interval_sec: float
    min_interval_sec: float
    max_interval_sec: float
    lengthen_step_sec: float = 0.0  # 0 => derive a gentle step from the range


def plan_next_interval(
    state: DecisionState,
    bounds: IntervalBounds,
    *,
    current_interval_sec: float,
) -> IntervalPlan:
    base = bounds.baseline_interval_sec
    lo = bounds.min_interval_sec
    hi = bounds.max_interval_sec
    step = bounds.lengthen_step_sec or max(1.0, (hi - base) * 0.25)

    if state == STRONG_VISITATION_CANDIDATE:
        nxt = _clamp(lo, lo, hi)
        return IntervalPlan(nxt, activity_score=1.0, reason="shorten_next_only_strong_candidate", transient=True)

    if state == UNCERTAIN_LOCAL_ACTIVITY:
        nxt = _clamp(base, lo, hi)
        return IntervalPlan(nxt, activity_score=0.5, reason="retain_baseline_uncertain_log_only")

    if state == ENVIRONMENTAL_NOISE:
        # Retain baseline, but if we have already drifted above it, allow a
        # cautious lengthen toward max rather than snapping back.
        nxt = _clamp(max(base, min(current_interval_sec + step, hi)), lo, hi)
        return IntervalPlan(nxt, activity_score=0.15, reason="retain_or_cautious_lengthen_noise")

    if state == NO_ACTIVITY:
        nxt = _clamp(current_interval_sec + step, lo, hi)
        return IntervalPlan(nxt, activity_score=0.0, reason="lengthen_toward_max_no_activity")

    raise ValueError(f"unknown decision state: {state!r}")


def _clamp(value: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, value)))
