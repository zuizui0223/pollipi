"""Versioned, approved policy profiles for probe-only shadow decisions."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

from pollipi_analysis.policy.three_stage import ThreeStageConfig, ThreeStageController

PROFILE_SCHEMA_VERSION = "pollipi-policy-profile-1"
DEFAULT_POLICY_PROFILE_ID = "three_stage_default_v1"
ALLOWED_POLICY_KINDS = frozenset({"three_stage", "rolling_median", "ml_classifier"})
PROFILE_RESOURCE_PACKAGE = "pollipi_analysis.policy_profiles"
_KIND_REQUIRED_PARAMETERS = {
    "three_stage": frozenset({
        "low_interval_sec",
        "mid_interval_sec",
        "high_interval_sec",
        "high_hard_cap_sec",
        "high_exit_quiet_probes",
    }),
    "rolling_median": frozenset({
        "window_size",
        "low_interval_sec",
        "high_interval_sec",
    }),
    "ml_classifier": frozenset({
        "model_id",
        "threshold",
        "low_interval_sec",
        "high_interval_sec",
    }),
}


@dataclass(frozen=True)
class PolicyProfile:
    """Approved profile selected at capture start and logged with shadow output."""

    schema: str
    profile_id: str
    simulation_run_id: str
    source_commit: str
    kind: str
    live_allowed: bool
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
            live_allowed=bool(data["live_allowed"]),
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
        if self.live_allowed is not False:
            raise ValueError(f"policy profile {self.profile_id} must set live_allowed=false")
        if not self.profile_id:
            raise ValueError("policy profile_id is required")
        if not self.simulation_run_id:
            raise ValueError(f"policy profile {self.profile_id} requires simulation_run_id")
        if not self.source_commit:
            raise ValueError(f"policy profile {self.profile_id} requires source_commit")
        required = _KIND_REQUIRED_PARAMETERS[self.kind]
        missing = required.difference(self.parameters)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"policy profile {self.profile_id} missing parameters: {missing_text}")
        if self.kind == "three_stage":
            for name in required:
                value = self.parameters[name]
                if name == "high_exit_quiet_probes":
                    if int(value) < 1:
                        raise ValueError(f"policy profile {self.profile_id} has invalid {name}")
                elif float(value) <= 0:
                    raise ValueError(f"policy profile {self.profile_id} has invalid {name}")


def _source_profile_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "policy_profiles"


def _installed_data_profile_dir() -> Path:
    return Path(sys.prefix) / "pollipi_analysis" / "policy_profiles"


def _load_profile_payloads_from_dir(directory: Path) -> list[Mapping[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
        if path.is_file()
    ]


def _load_profile_payloads_from_resources() -> list[Mapping[str, Any]]:
    try:
        root = resources.files(PROFILE_RESOURCE_PACKAGE)
    except (ModuleNotFoundError, FileNotFoundError):
        return []
    payloads: list[Mapping[str, Any]] = []
    for item in sorted(root.iterdir(), key=lambda entry: entry.name):
        if item.name.endswith(".json") and item.is_file():
            payloads.append(json.loads(item.read_text(encoding="utf-8")))
    return payloads


def _load_profile_payloads_from_embedded_bundle() -> list[Mapping[str, Any]]:
    try:
        from pollipi_analysis import policy_profile_bundle
    except ImportError:
        return []
    return [json.loads(raw) for _name, raw in sorted(policy_profile_bundle.PROFILE_JSON.items())]


def _load_profile_payloads() -> list[Mapping[str, Any]]:
    override = os.environ.get("POLLIPI_POLICY_PROFILE_DIR")
    if override:
        return _load_profile_payloads_from_dir(Path(override))

    source_dir = _source_profile_dir()
    if source_dir.is_dir():
        return _load_profile_payloads_from_dir(source_dir)

    resource_payloads = _load_profile_payloads_from_resources()
    if resource_payloads:
        return resource_payloads

    installed_dir = _installed_data_profile_dir()
    if installed_dir.is_dir():
        return _load_profile_payloads_from_dir(installed_dir)

    return _load_profile_payloads_from_embedded_bundle()


def _profile_index() -> dict[str, PolicyProfile]:
    profiles: dict[str, PolicyProfile] = {}
    for payload in _load_profile_payloads():
        profile = PolicyProfile.from_mapping(payload)
        if profile.profile_id in profiles:
            raise ValueError(f"duplicate policy profile_id: {profile.profile_id}")
        profiles[profile.profile_id] = profile
    if DEFAULT_POLICY_PROFILE_ID not in profiles:
        raise ValueError(f"default policy profile is missing: {DEFAULT_POLICY_PROFILE_ID}")
    return profiles


def list_policy_profiles() -> list[PolicyProfile]:
    return list(_profile_index().values())


def get_policy_profile(profile_id: str | None) -> PolicyProfile:
    selected = profile_id or DEFAULT_POLICY_PROFILE_ID
    profiles = _profile_index()
    try:
        return profiles[selected]
    except KeyError:
        raise KeyError(selected)


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
