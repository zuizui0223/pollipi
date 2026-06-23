"""Labelled scenario registry with the expected three-state outcome.

The expected labels encode the *current* (synthetic) calibration target, not a
field-validated ground truth. Mixed and low-SNR cases are deliberately labelled
``uncertain_local_activity`` because the six-round synthetic exploration showed
they cannot yet be separated reliably.
"""
from __future__ import annotations

from dataclasses import dataclass

from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
    DecisionState,
)


@dataclass(frozen=True)
class LabeledScenario:
    name: str
    expected: DecisionState
    family: str  # "target", "environment", or "mixed"


LABELED_SCENARIOS: tuple[LabeledScenario, ...] = (
    LabeledScenario("localized_trajectory", STRONG_VISITATION_CANDIDATE, "target"),
    LabeledScenario("boundary_crossing", STRONG_VISITATION_CANDIDATE, "target"),
    LabeledScenario("broad_wind", ENVIRONMENTAL_NOISE, "environment"),
    LabeledScenario("camera_shake", ENVIRONMENTAL_NOISE, "environment"),
    LabeledScenario("shadow", ENVIRONMENTAL_NOISE, "environment"),
    LabeledScenario("moving_shadow", ENVIRONMENTAL_NOISE, "environment"),
    LabeledScenario("oscillation", ENVIRONMENTAL_NOISE, "environment"),
    LabeledScenario("low_snr_target", UNCERTAIN_LOCAL_ACTIVITY, "mixed"),
    LabeledScenario("target_plus_wind", UNCERTAIN_LOCAL_ACTIVITY, "mixed"),
    LabeledScenario("target_plus_shadow", UNCERTAIN_LOCAL_ACTIVITY, "mixed"),
    LabeledScenario("target_plus_sway", UNCERTAIN_LOCAL_ACTIVITY, "mixed"),
)
