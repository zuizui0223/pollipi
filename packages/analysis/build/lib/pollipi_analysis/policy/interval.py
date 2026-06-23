"""Rule-based adaptive interval policy shared by simulation and Pi runtime."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntervalDecision:
    next_interval_sec: float
    activity_score: float
    reason: str


def decide_next_interval(
    *,
    baseline_interval_sec: float,
    min_interval_sec: float,
    max_interval_sec: float,
    current_interval_sec: float,
    candidate_rate: float,
    visit_likeness: float,
    noise_likeness: float,
) -> IntervalDecision:
    activity_score = max(
        0.0,
        min(1.0, (0.55 * candidate_rate) + (0.35 * visit_likeness) - (0.20 * noise_likeness)),
    )
    target = baseline_interval_sec - activity_score * (baseline_interval_sec - min_interval_sec)
    target = max(min_interval_sec, min(max_interval_sec, target))
    next_interval = (0.7 * current_interval_sec) + (0.3 * target)
    next_interval = max(min_interval_sec, min(max_interval_sec, next_interval))
    reason = (
        f"Adaptive interval from activity_score={activity_score:.3f}, "
        f"candidate_rate={candidate_rate:.3f}, visit_like={visit_likeness:.3f}, "
        f"noise_like={noise_likeness:.3f}."
    )
    return IntervalDecision(next_interval, activity_score, reason)
