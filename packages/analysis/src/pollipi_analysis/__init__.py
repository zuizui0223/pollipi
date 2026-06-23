"""Pure analysis package for PolliPi field runtime and laptop simulation.

No FastAPI, no Picamera2, no required filesystem dependency. The simulator and
the Pi runtime import the *same* feature, classifier, and policy functions from
here so calibration matches production behaviour.
"""
from pollipi_analysis.pipeline import (
    ClassifierConfig,
    PipelineConfig,
    analyze,
    classify_features,
)
from pollipi_analysis.policy.state_policy import (
    IntervalBounds,
    IntervalPlan,
    plan_next_interval,
)
from pollipi_analysis.schemas import (
    ACTIVE_DECISION_STATES,
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
    MeshDecision,
    MeshFeatures,
    ShadowDecisionRecord,
)
from pollipi_analysis.shadow import run_shadow_mode
from pollipi_analysis.abtest import ABComparison, compare_policies

__version__ = "0.2.0"

__all__ = [
    "analyze",
    "classify_features",
    "PipelineConfig",
    "ClassifierConfig",
    "plan_next_interval",
    "IntervalBounds",
    "IntervalPlan",
    "run_shadow_mode",
    "compare_policies",
    "ABComparison",
    "MeshDecision",
    "MeshFeatures",
    "ShadowDecisionRecord",
    "NO_ACTIVITY",
    "ENVIRONMENTAL_NOISE",
    "UNCERTAIN_LOCAL_ACTIVITY",
    "STRONG_VISITATION_CANDIDATE",
    "ACTIVE_DECISION_STATES",
]
