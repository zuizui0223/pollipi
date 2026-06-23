"""Load the Pi's mesh policy artifact at startup (Issue #21).

The Pi reads a ``simulation_informed_policy.json`` (if present) to construct its
``PipelineConfig``. It NEVER runs the simulation, parameter search, pandas, or
matplotlib — it only loads numeric thresholds and classifies real images.

If no policy file is present (or it fails to parse), a built-in baseline rule
config is used so the device always has a safe, working configuration.
"""
from __future__ import annotations

from pollipi_analysis.pipeline import PipelineConfig
from pollipi_analysis.policy.artifact import PolicyMeta, load_policy

from visit_monitor_server.config import POLICY_PATH

_DEFAULT_META = PolicyMeta(
    policy_name="baseline_rule",
    policy_version="0",
    validation_status="synthetic_only",
)


def get_active_policy() -> tuple[PipelineConfig, PolicyMeta]:
    """Return ``(pipeline_config, meta)`` for the active mesh policy.

    Reads ``POLICY_PATH`` on each call (the file is tiny and read at most once
    per capture-loop start / status request). Falls back to the baseline config
    if the file is absent or unparseable.
    """
    if POLICY_PATH.is_file():
        try:
            return load_policy(POLICY_PATH)
        except Exception:
            # A malformed policy must not take the device down; log-and-fallback.
            pass
    return PipelineConfig(), _DEFAULT_META
