"""Versioned, approved policy profiles for probe-only shadow decisions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from pollipi_analysis.policy.three_stage import ThreeStageConfig, ThreeStageController

PROFILE_SCHEMA_VERSION = "pollipi-policy-profile-1"
DEFAULT_POLICY_PROFILE_ID = "three_stage_default_v1"
ALLOWED_POLICY_KINDS = frozenset({"three_stage", "rolling_median", "ml_classifier"})


@dataclass(frozen=True)
class PolicyProfile:
    """Approved profile selected at capture start and logged with shadow output."""

    schema: str
    profile_id: str
    simulation_run_id: str
    source_commit: str
    kind: str
    parameters: Mapping[str, Any]
    description: str = ""

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PolicyProfile":
        profile = cls(
            schema=str(data["schema"]),
            profile_id=str(data["profile_id"]),
            simulation_run_id=str(data["simulation_run_id"]),
            source_commit=str(data["source_commit"]),
            kind=str(data["kind"]),
            parameters=dict(data["parameters"]),
            description=str(data.get("description", "")),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        if self.schema != PROFILE_SCHEMA_VERSION:
            raise ValueError(f"unsupported policy profile schema: {self.schema}")
        if self.kind not in ALLOWED_POLICY_KINDS:
            raise ValueError(f"unsupported policy profile kind: {self.kind}")
        if not self.profile_id:
            raise ValueError("policy profile_id is required")


_BUILTIN_PROFILE_DATA: dict[str, dict[str, Any]] = {
    DEFAULT_POLICY_PROFILE_ID: {
        "schema": PROFILE_SCHEMA_VERSION,
        "profile_id": DEFAULT_POLICY_PROFILE_ID,
        "simulation_run_id": "issue27-three-stage-baseline",
        "source_commit": "af2b561",
        "kind": "three_stage",
        "description": "Default shadow-only three-stage profile; keeps 30s high-res capture fixed.",
        "parameters": {
            "low_interval_sec": 30.0,
            "mid_interval_sec": 15.0,
            "high_interval_sec": 5.0,
            "high_hard_cap_sec": 120.0,
            "high_exit_quiet_probes": 3,
        },
    },
    "three_stage_sensitive_v1": {
        "schema": PROFILE_SCHEMA_VERSION,
        "profile_id": "three_stage_sensitive_v1",
        "simulation_run_id": "issue27-three-stage-sensitive",
        "source_commit": "af2b561",
        "kind": "three_stage",
        "description": "More persistent high shadow response for PC simulation comparison only.",
        "parameters": {
            "low_interval_sec": 30.0,
            "mid_interval_sec": 10.0,
            "high_interval_sec": 5.0,
            "high_hard_cap_sec": 180.0,
            "high_exit_quiet_probes": 4,
        },
    },
}


def list_policy_profiles() -> list[PolicyProfile]:
    return [PolicyProfile.from_mapping(data) for data in _BUILTIN_PROFILE_DATA.values()]


def get_policy_profile(profile_id: str | None) -> PolicyProfile:
    selected = profile_id or DEFAULT_POLICY_PROFILE_ID
    data = _BUILTIN_PROFILE_DATA.get(selected)
    if data is None:
        raise KeyError(selected)
    return PolicyProfile.from_mapping(data)


def three_stage_config_from_profile(profile: PolicyProfile) -> ThreeStageConfig:
    if profile.kind != "three_stage":
        raise ValueError(f"policy profile kind is not active on Pi: {profile.kind}")
    params = profile.parameters
    return ThreeStageConfig(
        low_interval_sec=float(params["low_interval_sec"]),
        mid_interval_sec=float(params["mid_interval_sec"]),
        high_interval_sec=float(params["high_interval_sec"]),
        high_hard_cap_sec=float(params["high_hard_cap_sec"]),
        high_exit_quiet_probes=int(params["high_exit_quiet_probes"]),
    )


def create_policy_controller(profile: PolicyProfile) -> ThreeStageController:
    """Factory boundary for future rolling_median and ml_classifier profiles."""
    if profile.kind != "three_stage":
        raise ValueError(f"policy profile kind is not active on Pi: {profile.kind}")
    return ThreeStageController(three_stage_config_from_profile(profile))
