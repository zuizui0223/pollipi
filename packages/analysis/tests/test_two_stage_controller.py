"""Two-stage LOW/HIGH controller semantics (Phase 2/4 shared state machine)."""
from __future__ import annotations

import pytest

from pollipi_analysis.policy.two_stage import HIGH, LOW, TwoStageConfig, TwoStageController
from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)

CFG = TwoStageConfig(low_rate_sec=30.0, high_rate_sec=5.0, high_hold_sec=120.0)


def test_defaults_to_low_rate() -> None:
    c = TwoStageController(config=CFG)
    step = c.step(NO_ACTIVITY, now_sec=0.0)
    assert step.mode == LOW and step.interval_sec == 30.0


@pytest.mark.parametrize("state", [NO_ACTIVITY, ENVIRONMENTAL_NOISE, UNCERTAIN_LOCAL_ACTIVITY])
def test_non_trigger_states_never_enter_high(state) -> None:
    c = TwoStageController(config=CFG)
    assert c.step(state, now_sec=0.0).mode == LOW


def test_strong_candidate_enters_high_for_the_hold_window() -> None:
    c = TwoStageController(config=CFG)
    step = c.step(STRONG_VISITATION_CANDIDATE, now_sec=0.0)
    assert step.mode == HIGH and step.interval_sec == 5.0 and step.triggered
    # Still HIGH partway through the 120s hold even with no new trigger.
    assert c.step(NO_ACTIVITY, now_sec=60.0).mode == HIGH
    assert c.step(NO_ACTIVITY, now_sec=119.0).mode == HIGH
    # Hold expires -> back to LOW.
    back = c.step(NO_ACTIVITY, now_sec=121.0)
    assert back.mode == LOW and back.interval_sec == 30.0


def test_new_trigger_re_arms_the_hold() -> None:
    c = TwoStageController(config=CFG)
    c.step(STRONG_VISITATION_CANDIDATE, now_sec=0.0)
    # Re-trigger at t=100 extends HIGH to t=220.
    c.step(STRONG_VISITATION_CANDIDATE, now_sec=100.0)
    assert c.step(NO_ACTIVITY, now_sec=200.0).mode == HIGH
    assert c.step(NO_ACTIVITY, now_sec=221.0).mode == LOW


def test_invalid_config_rejected() -> None:
    with pytest.raises(ValueError):
        TwoStageConfig(low_rate_sec=5.0, high_rate_sec=30.0)
