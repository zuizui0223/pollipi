"""Phase E: shadow-mode A/B comparison of two policies."""
from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.abtest import compare_policies
from pollipi_analysis.features.compute import FeatureConfig
from pollipi_analysis.pipeline import ClassifierConfig, PipelineConfig
from pollipi_analysis.policy.state_policy import IntervalBounds
from pollipi_analysis.simulation.synthetic import simulate_sequence

BOUNDS = IntervalBounds(baseline_interval_sec=60, min_interval_sec=10, max_interval_sec=180)
BASELINE = PipelineConfig()
CANDIDATE = PipelineConfig(
    features=FeatureConfig(cell_size=24, pixel_difference=20),
    classifier=ClassifierConfig(strong_spatial_concentration=0.55),
)


def test_identical_policies_fully_agree() -> None:
    frames = simulate_sequence("target_traverse", n_frames=8, seed=7)
    result = compare_policies(frames, bounds=BOUNDS, config_a=BASELINE, config_b=BASELINE)
    assert result.n_frames > 0
    assert result.agreement_rate == 1.0
    assert result.disagreements == []
    assert result.b_more_aggressive == 0 and result.a_more_aggressive == 0


def test_comparison_reports_well_formed_metrics() -> None:
    frames = simulate_sequence("local_sway", n_frames=8, seed=7)
    result = compare_policies(
        frames, bounds=BOUNDS, config_a=BASELINE, config_b=CANDIDATE,
        policy_a_name="baseline_rule", policy_b_name="simulation_informed",
    )
    assert result.n_frames > 0
    assert 0.0 <= result.agreement_rate <= 1.0
    # Disagreement count is consistent with the agreement rate.
    assert len(result.disagreements) == result.n_frames - round(result.agreement_rate * result.n_frames)
    d = result.to_dict()
    assert {"agreement_rate", "b_more_aggressive", "a_strong", "b_strong"} <= set(d)
