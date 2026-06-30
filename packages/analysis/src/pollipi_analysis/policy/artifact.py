"""Versioned, Pi-loadable mesh policy artifact (Issue #21).

A policy artifact is a small JSON file produced on a development machine by the
cost-weighted simulation search. The Pi runtime loads it at startup to construct
its :class:`PipelineConfig` — it never runs the simulation, parameter search,
pandas, or matplotlib.

The artifact contains ONLY Pi-compatible fields: the numeric ``FeatureConfig`` and
``ClassifierConfig`` values used by ``pollipi_analysis.pipeline``, plus provenance
metadata. ``validation_status`` stays ``"synthetic_only"`` until real Pi field
data validates the thresholds (never ``field_validated`` / ``production`` yet).

This module imports only stdlib + the shared config dataclasses, so importing it
on the Pi pulls in no simulation dependencies.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields as dataclass_fields
from pathlib import Path
from typing import Any, Optional, Union

from pollipi_analysis.features.compute import FeatureConfig
from pollipi_analysis.pipeline import ClassifierConfig, PipelineConfig

POLICY_SCHEMA_VERSION = "policy-1"
DEFAULT_VALIDATION_STATUS = "synthetic_only"
_ALLOWED_VALIDATION = {"synthetic_only", "simulation_informed"}


@dataclass(frozen=True)
class PolicyMeta:
    policy_name: str
    policy_version: str
    validation_status: str = DEFAULT_VALIDATION_STATUS
    seed: Optional[int] = None
    generated_at: Optional[str] = None
    notes: str = ""


def build_policy(config: PipelineConfig, meta: PolicyMeta) -> dict[str, Any]:
    """Serialise a pipeline config + provenance into a Pi-loadable dict."""
    if meta.validation_status not in _ALLOWED_VALIDATION:
        raise ValueError(
            f"validation_status must be one of {_ALLOWED_VALIDATION}; "
            f"got {meta.validation_status!r} (no field_validated/production yet)"
        )
    return {
        "schema": POLICY_SCHEMA_VERSION,
        "policy_name": meta.policy_name,
        "policy_version": meta.policy_version,
        "validation_status": meta.validation_status,
        "metadata": {
            "seed": meta.seed,
            "generated_at": meta.generated_at,
            "notes": meta.notes,
        },
        "feature": asdict(config.features),
        "classifier": asdict(config.classifier),
    }


def _known_fields(cls: type, values: dict[str, Any]) -> dict[str, Any]:
    """Keep only keys that are still fields of ``cls``.

    Tolerates forward/backward schema drift: an older artifact may carry numeric
    fields that have since been removed (e.g. the retired oscillation_* gates), so
    we drop unknown keys rather than crash, while still honouring every field the
    current dataclass defines.
    """
    allowed = {f.name for f in dataclass_fields(cls)}
    return {k: v for k, v in values.items() if k in allowed}


def policy_to_pipeline_config(policy: dict[str, Any]) -> PipelineConfig:
    """Reconstruct a :class:`PipelineConfig` from a policy dict."""
    feature = FeatureConfig(**_known_fields(FeatureConfig, policy["feature"]))
    classifier = ClassifierConfig(**_known_fields(ClassifierConfig, policy["classifier"]))
    return PipelineConfig(features=feature, classifier=classifier)


def write_policy(path: Union[str, Path], config: PipelineConfig, meta: PolicyMeta) -> Path:
    out = Path(path)
    out.write_text(json.dumps(build_policy(config, meta), indent=2), encoding="utf-8")
    return out


def load_policy(source: Union[str, Path, dict[str, Any]]) -> tuple[PipelineConfig, PolicyMeta]:
    """Load a policy from a JSON file path or an already-parsed dict.

    Returns ``(pipeline_config, meta)``. Raises ``ValueError`` on a missing or
    mismatched schema so the Pi fails loudly rather than running a bad policy.
    """
    if isinstance(source, dict):
        data = source
    else:
        data = json.loads(Path(source).read_text(encoding="utf-8"))

    schema = data.get("schema")
    if schema != POLICY_SCHEMA_VERSION:
        raise ValueError(f"unsupported policy schema {schema!r}; expected {POLICY_SCHEMA_VERSION!r}")

    config = policy_to_pipeline_config(data)
    meta = PolicyMeta(
        policy_name=data["policy_name"],
        policy_version=str(data["policy_version"]),
        validation_status=data.get("validation_status", DEFAULT_VALIDATION_STATUS),
        seed=(data.get("metadata") or {}).get("seed"),
        generated_at=(data.get("metadata") or {}).get("generated_at"),
        notes=(data.get("metadata") or {}).get("notes", ""),
    )
    return config, meta
