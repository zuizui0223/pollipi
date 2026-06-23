"""Canonical decision vocabulary for adaptive-timelapse mesh analysis.

Per Issue #14/#15 research design the active decision states are exactly:

- ``environmental_noise``
- ``uncertain_local_activity``
- ``strong_visitation_candidate``

``no_activity`` is the resting state used by the interval policy to drift toward
the maximum interval. A mesh decision state is NEVER a confirmed pollinator
visit: confirmed visitation is evaluated later from the scheduled timelapse
images, accounting for variable-interval sampling effort.
"""
from __future__ import annotations

from typing import Literal

DecisionState = Literal[
    "no_activity",
    "environmental_noise",
    "uncertain_local_activity",
    "strong_visitation_candidate",
]

NO_ACTIVITY: DecisionState = "no_activity"
ENVIRONMENTAL_NOISE: DecisionState = "environmental_noise"
UNCERTAIN_LOCAL_ACTIVITY: DecisionState = "uncertain_local_activity"
STRONG_VISITATION_CANDIDATE: DecisionState = "strong_visitation_candidate"

# The three "active" states an analysed frame pair can produce.
ACTIVE_DECISION_STATES: tuple[DecisionState, ...] = (
    ENVIRONMENTAL_NOISE,
    UNCERTAIN_LOCAL_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
)

# Every state the policy understands, including the resting state.
ALL_DECISION_STATES: tuple[DecisionState, ...] = (
    NO_ACTIVITY,
    *ACTIVE_DECISION_STATES,
)
