"""Independent field-truth contract for TNOA/PolliPi validation.

The annotation layer is deliberately separate from algorithm evidence.  Biological
truth comes from an independent reference stream; primary-stream observability is
annotated separately; nuisance is multi-label; and unresolved reference truth is
never converted to absence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet


class BiologicalTruth(str, Enum):
    NO_INSECT = "no_insect"
    INSECT_IN_CONTEXT = "insect_in_context"
    TARGET_CONTACT = "target_contact"
    VISIT_EVENT = "visit_event"
    TRUTH_UNRESOLVED = "truth_unresolved"


class CoupledTruth(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    UNRESOLVED = "unresolved"


class ObservabilityTruth(str, Enum):
    OBSERVABLE = "observable"
    COMPROMISED = "compromised"
    UNOBSERVABLE = "unobservable"


NUISANCE_EFFECTS = frozenset({"mimic", "mask", "corrupt_attribution", "degrade_observation"})
NUISANCE_FAMILIES = frozenset({
    "wind_target_motion",
    "camera_shake",
    "moving_shadow",
    "illumination_change",
    "occlusion",
    "blur",
    "non_target_actor",
    "other_exogenous",
})


@dataclass(frozen=True, slots=True)
class IndependentTruthRecord:
    window_id: str
    recording_day: str
    focal_scene_id: str
    recording_block: str
    reference_source_id: str
    biological_truth: BiologicalTruth
    coupled_truth: CoupledTruth
    observability_truth: ObservabilityTruth
    nuisance_families: FrozenSet[str] = frozenset()
    nuisance_effects: FrozenSet[str] = frozenset()
    annotator_id: str = ""
    adjudicated: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("window_id", self.window_id),
            ("recording_day", self.recording_day),
            ("focal_scene_id", self.focal_scene_id),
            ("recording_block", self.recording_block),
            ("reference_source_id", self.reference_source_id),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} is required")
        unknown_families = set(self.nuisance_families) - NUISANCE_FAMILIES
        if unknown_families:
            raise ValueError(f"unknown nuisance families: {sorted(unknown_families)}")
        unknown_effects = set(self.nuisance_effects) - NUISANCE_EFFECTS
        if unknown_effects:
            raise ValueError(f"unknown nuisance effects: {sorted(unknown_effects)}")
        if self.coupled_truth is CoupledTruth.PRESENT and self.biological_truth not in {
            BiologicalTruth.TARGET_CONTACT,
            BiologicalTruth.VISIT_EVENT,
        }:
            raise ValueError("coupled present requires resolved target_contact or visit_event truth")
        if self.biological_truth is BiologicalTruth.TRUTH_UNRESOLVED and self.coupled_truth is CoupledTruth.PRESENT:
            raise ValueError("unresolved biological truth cannot certify target-coupled response")

    @property
    def split_group(self) -> str:
        """Minimum leakage-safe split unit: day x scene x recording block."""
        return f"{self.recording_day}|{self.focal_scene_id}|{self.recording_block}"

    @property
    def resolved_biological_truth(self) -> bool:
        return self.biological_truth is not BiologicalTruth.TRUTH_UNRESOLVED
