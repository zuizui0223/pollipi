"""Phase 3: the Pi loads baseline (A) + simulation-informed (B) for shadow A/B."""
from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.features.compute import FeatureConfig
from pollipi_analysis.pipeline import ClassifierConfig, PipelineConfig
from pollipi_analysis.policy.artifact import PolicyMeta, write_policy

from visit_monitor_server.services import policy_runtime


def test_no_artifact_disables_ab(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(policy_runtime, "POLICY_PATH", tmp_path / "missing.json")
    (a_cfg, a_meta), (b_cfg, b_meta), ab_enabled = policy_runtime.get_ab_policies()
    assert ab_enabled is False
    # A and B are both the built-in baseline when no policy file exists.
    assert a_meta.policy_name == "baseline_rule"
    assert b_meta.policy_name == "baseline_rule"


def test_artifact_enables_ab_with_distinct_b(monkeypatch, tmp_path) -> None:
    policy_path = tmp_path / "simulation_informed_policy.json"
    write_policy(
        policy_path,
        PipelineConfig(
            features=FeatureConfig(cell_size=48, pixel_difference=30),
            classifier=ClassifierConfig(strong_spatial_concentration=0.85),
        ),
        PolicyMeta(policy_name="simulation_informed", policy_version="1", validation_status="simulation_informed"),
    )
    monkeypatch.setattr(policy_runtime, "POLICY_PATH", policy_path)

    (a_cfg, a_meta), (b_cfg, b_meta), ab_enabled = policy_runtime.get_ab_policies()
    assert ab_enabled is True
    assert a_meta.policy_name == "baseline_rule"
    assert b_meta.policy_name == "simulation_informed"
    # B carries the artifact's thresholds; A stays at the baseline defaults.
    assert b_cfg.features.cell_size == 48
    assert a_cfg.features.cell_size == FeatureConfig().cell_size
