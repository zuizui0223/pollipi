"""Guards for TNOA field-calibration manifests.

The pre-data manifest is intentionally unusable for held-out scoring or live Pi
actions.  A later frozen manifest must be introduced explicitly rather than by
silently filling synthetic thresholds into this file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

UNFROZEN_SCHEMA = "tnoa-field-calibration-manifest-v1"


def load_manifest(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != UNFROZEN_SCHEMA:
        raise ValueError("unexpected TNOA field-calibration schema")
    return payload


def validate_unfrozen_manifest(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != UNFROZEN_SCHEMA:
        raise ValueError("unexpected TNOA field-calibration schema")
    if payload.get("status") != "unfrozen_predata":
        raise ValueError("this guard validates only the unfrozen pre-data manifest")
    if payload.get("independent_reference_truth_required") is not True:
        raise ValueError("independent reference truth must remain required")
    if payload.get("split_group") != ["recording_day", "focal_scene_id", "recording_block"]:
        raise ValueError("leakage-safe split group drifted")
    if float(payload.get("minimum_double_annotation_fraction", 0.0)) < 0.2:
        raise ValueError("at least 20% double annotation must remain registered")
    if payload.get("heldout_scoring_allowed") is not False:
        raise ValueError("held-out scoring cannot be enabled before calibration freeze")
    if payload.get("live_tnoa_capture_actions_allowed") is not False:
        raise ValueError("live TNOA actions cannot be enabled by an unfrozen manifest")

    target = payload.get("target", {})
    nuisance = payload.get("nuisance", {})
    observability = payload.get("observability", {})
    coupled = payload.get("coupled", {})
    absence = payload.get("target_absence", {})
    for value, label in (
        (target.get("high_threshold"), "target.high_threshold"),
        (target.get("low_threshold"), "target.low_threshold"),
        (target.get("operational_error_criterion"), "target.operational_error_criterion"),
        (nuisance.get("familywise_false_attribution_alpha"), "nuisance.familywise_false_attribution_alpha"),
        (observability.get("support_rule"), "observability.support_rule"),
        (observability.get("observable_thresholds"), "observability.observable_thresholds"),
        (observability.get("unobservable_thresholds"), "observability.unobservable_thresholds"),
        (coupled.get("response_threshold"), "coupled.response_threshold"),
        (coupled.get("target_link_threshold"), "coupled.target_link_threshold"),
        (absence.get("rule"), "target_absence.rule"),
    ):
        if value is not None:
            raise ValueError(f"unfrozen manifest must not define {label}")
    if coupled.get("enabled_for_target_rescue") is not False:
        raise ValueError("coupled target rescue must remain disabled pre-freeze")
    if absence.get("channel_status") != "unavailable":
        raise ValueError("target-absence channel must remain unavailable pre-freeze")


def assert_not_runtime_usable(payload: Mapping[str, Any]) -> None:
    """Raise unless the supplied manifest is explicitly frozen for runtime use."""
    if payload.get("status") != "frozen_field_calibration":
        raise RuntimeError("TNOA field calibration is not frozen; runtime decisions are forbidden")
    if payload.get("heldout_scoring_allowed") is not True:
        raise RuntimeError("held-out scoring has not been licensed")
    if payload.get("live_tnoa_capture_actions_allowed") is not True:
        raise RuntimeError("live TNOA capture actions have not been licensed")
