"""Shared, serialisable contracts for PolliPi mesh analysis.

These types are pure data: no numpy, no FastAPI, no Picamera2, no filesystem.
They are the single source of truth for the decision vocabulary used by both the
laptop simulator and the Pi runtime.
"""
from pollipi_analysis.schemas.states import (
    ACTIVE_DECISION_STATES,
    ALL_DECISION_STATES,
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
    DecisionState,
)
from pollipi_analysis.schemas.features import MeshFeatures
from pollipi_analysis.schemas.decision import MeshDecision
from pollipi_analysis.schemas.shadow import (
    SHADOW_LOG_COLUMNS,
    SHADOW_LOG_VERSION,
    ShadowDecisionRecord,
)

__all__ = [
    "DecisionState",
    "NO_ACTIVITY",
    "ENVIRONMENTAL_NOISE",
    "UNCERTAIN_LOCAL_ACTIVITY",
    "STRONG_VISITATION_CANDIDATE",
    "ACTIVE_DECISION_STATES",
    "ALL_DECISION_STATES",
    "MeshFeatures",
    "MeshDecision",
    "ShadowDecisionRecord",
    "SHADOW_LOG_COLUMNS",
    "SHADOW_LOG_VERSION",
]
