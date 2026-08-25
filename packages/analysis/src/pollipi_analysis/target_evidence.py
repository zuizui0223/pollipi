"""Portable target-evidence contract for cross-observer visit sensing.

PolliPi states are not visit truth and are not nuisance truth. This module maps the
existing ordinal mesh-decision vocabulary to an explicit target-evidence record
that another repository can consume without importing PolliPi decision logic.

The numeric score is an ordinal reference encoding, not a calibrated probability:

- no_activity -> 0.0
- environmental_noise -> 0.0
- uncertain_local_activity -> 0.5
- strong_visitation_candidate -> 1.0

The important V14 separation is that ``environmental_noise`` means PolliPi did not
retain strong target evidence from that frame pair. Whether the scene truly
contains nuisance, how severe that nuisance is, and whether the interaction zone
was observable are separate questions handled outside this adapter.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from pollipi_analysis.schemas.states import (
    ALL_DECISION_STATES,
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
    DecisionState,
)


REFERENCE_TARGET_EVIDENCE: dict[DecisionState, float] = {
    NO_ACTIVITY: 0.0,
    ENVIRONMENTAL_NOISE: 0.0,
    UNCERTAIN_LOCAL_ACTIVITY: 0.5,
    STRONG_VISITATION_CANDIDATE: 1.0,
}


@dataclass(frozen=True, slots=True)
class TargetEvidenceRecord:
    """Observer-E output that makes no biological-truth claim."""

    source_state: DecisionState
    score: float
    scale: str = "ordinal-v14-reference"
    confirmed_visit: bool = False

    def __post_init__(self) -> None:
        if self.source_state not in ALL_DECISION_STATES:
            raise ValueError(f"unsupported PolliPi state: {self.source_state!r}")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("target evidence score must lie in [0, 1]")
        if self.confirmed_visit:
            raise ValueError("PolliPi target evidence cannot be marked as confirmed visitation")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def to_target_evidence(state: DecisionState) -> TargetEvidenceRecord:
    """Convert a canonical PolliPi state to the V14 ordinal evidence contract."""

    try:
        score = REFERENCE_TARGET_EVIDENCE[state]
    except KeyError as exc:
        raise ValueError(f"unsupported PolliPi state: {state!r}") from exc
    return TargetEvidenceRecord(source_state=state, score=score)
