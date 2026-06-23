from __future__ import annotations

from pollipi_analysis.policy.state_policy import IntervalBounds, plan_next_interval
from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)

BOUNDS = IntervalBounds(baseline_interval_sec=60, min_interval_sec=10, max_interval_sec=180)


def test_strong_candidate_shortens_only_next_interval() -> None:
    plan = plan_next_interval(STRONG_VISITATION_CANDIDATE, BOUNDS, current_interval_sec=60)
    assert plan.next_interval_sec == 10  # shortened toward minimum
    assert plan.transient is True  # baseline is not changed; next interval only


def test_uncertain_retains_baseline_and_logs_only() -> None:
    plan = plan_next_interval(UNCERTAIN_LOCAL_ACTIVITY, BOUNDS, current_interval_sec=120)
    assert plan.next_interval_sec == 60  # back to baseline
    assert plan.transient is False


def test_no_activity_drifts_toward_maximum() -> None:
    plan = plan_next_interval(NO_ACTIVITY, BOUNDS, current_interval_sec=60)
    assert plan.next_interval_sec > 60
    assert plan.next_interval_sec <= 180


def test_noise_retains_or_cautiously_lengthens_never_shortens() -> None:
    at_baseline = plan_next_interval(ENVIRONMENTAL_NOISE, BOUNDS, current_interval_sec=60)
    already_long = plan_next_interval(ENVIRONMENTAL_NOISE, BOUNDS, current_interval_sec=120)
    assert at_baseline.next_interval_sec >= 60
    assert already_long.next_interval_sec >= 120


def test_interval_is_always_within_bounds() -> None:
    for state in (
        STRONG_VISITATION_CANDIDATE,
        UNCERTAIN_LOCAL_ACTIVITY,
        ENVIRONMENTAL_NOISE,
        NO_ACTIVITY,
    ):
        plan = plan_next_interval(state, BOUNDS, current_interval_sec=200)
        assert 10 <= plan.next_interval_sec <= 180
