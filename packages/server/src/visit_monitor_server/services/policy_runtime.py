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


def get_baseline_policy() -> tuple[PipelineConfig, PolicyMeta]:
    """Return the built-in baseline rule config (policy A in shadow A/B)."""
    return PipelineConfig(), _DEFAULT_META


def get_ab_policies() -> tuple[
    tuple[PipelineConfig, PolicyMeta], tuple[PipelineConfig, PolicyMeta], bool
]:
    """Return ``(policy_a, policy_b, ab_enabled)`` for shadow A/B comparison.

    A is always the built-in ``baseline_rule``; B is the simulation-informed
    artifact when one is present. ``ab_enabled`` is True only when B differs from
    A (i.e. an artifact was actually loaded), so the device does not log a
    pointless A-vs-A comparison when no policy file exists. Neither policy changes
    capture timing — both run in shadow until field A/B validates B.
    """
    policy_a = get_baseline_policy()
    policy_b = get_active_policy()
    ab_enabled = policy_b[1].policy_name != policy_a[1].policy_name
    return policy_a, policy_b, ab_enabled
