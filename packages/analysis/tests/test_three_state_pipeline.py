from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.schemas.states import (
    ACTIVE_DECISION_STATES,
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
)
from pollipi_analysis.simulation.scenarios import LABELED_SCENARIOS
from pollipi_analysis.simulation.synthetic import simulate_pair

CLEAN_TARGETS = ("localized_trajectory", "boundary_crossing")
PURE_ENVIRONMENT = ("broad_wind", "camera_shake", "shadow", "moving_shadow")


def _state(scenario: str):
    background, frame = simulate_pair(scenario, seed=7)
    return analyze(frame, background).state


def test_clean_targets_are_strong_candidates() -> None:
    for scenario in CLEAN_TARGETS:
        assert _state(scenario) == STRONG_VISITATION_CANDIDATE, scenario


def test_pure_environment_is_environmental_noise() -> None:
    for scenario in PURE_ENVIRONMENT:
        assert _state(scenario) == ENVIRONMENTAL_NOISE, scenario


def test_environment_never_triggers_a_strong_candidate() -> None:
    # The expensive failure mode in the field is a false strong candidate that
    # shortens the interval. No environment-family scenario may do that.
    for scenario in LABELED_SCENARIOS:
        if scenario.family != "environment":
            continue
        assert _state(scenario.name) != STRONG_VISITATION_CANDIDATE, scenario.name


def test_decision_state_is_always_in_the_canonical_vocabulary() -> None:
    allowed = {NO_ACTIVITY, *ACTIVE_DECISION_STATES}
    for scenario in LABELED_SCENARIOS:
        assert _state(scenario.name) in allowed, scenario.name


def test_decision_is_explainable_and_carries_features() -> None:
    background, frame = simulate_pair("localized_trajectory", seed=7)
    decision = analyze(frame, background)
    assert decision.reason  # non-empty stable token
    flat = decision.flat()
    assert flat["decision_state"] == decision.state
    assert "active_cell_proportion" in flat
    assert flat["mesh_layout"] == "rectangular_offset_baseline"


def test_brightness_normalisation_keeps_small_target_not_median_subtraction() -> None:
    # Median background subtraction can erase weak targets; the default path uses
    # brightness normalisation only and must still retain a clean small target.
    background, frame = simulate_pair("localized_trajectory", seed=11)
    assert analyze(frame, background).state == STRONG_VISITATION_CANDIDATE
