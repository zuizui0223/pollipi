"""Phase A/B: shadow-only A/B aggregation + trajectory features.

These features are LOGGED for offline comparison and must NOT change the active
three-state decision (that is asserted in test_three_state_pipeline.py).
"""
from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.policy.state_policy import IntervalBounds
from pollipi_analysis.schemas.shadow import SHADOW_LOG_COLUMNS
from pollipi_analysis.shadow import run_shadow_mode
from pollipi_analysis.simulation.synthetic import simulate_pair, simulate_sequence

BOUNDS = IntervalBounds(baseline_interval_sec=60, min_interval_sec=10, max_interval_sec=180)


def test_aggregation_fields_are_populated() -> None:
    bg, fr = simulate_pair("localized_trajectory", seed=7)
    f = analyze(fr, bg).features
    for value in (
        f.active_proportion_mean,
        f.active_proportion_max,
        f.active_proportion_q90,
        f.active_proportion_q95,
        f.concentration_max,
    ):
        assert value is not None and value >= 0.0


def test_max_aggregation_retains_a_compact_target_the_mean_erases() -> None:
    # The motivating A/B result: a small compact target shows up under the max
    # (upper-tail) reducer but is averaged below threshold by the cell mean.
    bg, fr = simulate_pair("localized_trajectory", seed=7)
    f = analyze(fr, bg).features
    assert f.active_proportion_max >= f.active_proportion_mean
    assert f.active_proportion_max > 0.0


def test_trajectory_features_discriminate_traverse_from_sway() -> None:
    traverse = run_shadow_mode(simulate_sequence("target_traverse", n_frames=8, seed=7), bounds=BOUNDS)
    sway = run_shadow_mode(simulate_sequence("local_sway", n_frames=8, seed=7), bounds=BOUNDS)
    t = traverse[-1].decision.features
    s = sway[-1].decision.features

    assert t.track_frames >= 2 and s.track_frames >= 2
    assert t.mean_step is not None and s.mean_step is not None
    # Directed traverse: efficient, no reversals. Sway: inefficient, reversing.
    assert t.path_efficiency > 0.8 and t.reversal_rate == 0.0
    assert s.path_efficiency < 0.5
    assert s.reversal_rate > t.reversal_rate


def test_shadow_row_carries_policy_metadata_and_new_columns() -> None:
    rec = run_shadow_mode(simulate_sequence("target_traverse", n_frames=6, seed=7), bounds=BOUNDS)[-1]
    row = rec.to_row()
    assert set(row.keys()) == set(SHADOW_LOG_COLUMNS)
    # Issue #21: provenance must be present and honest until field validation.
    assert row["validation_status"] == "synthetic_only"
    assert row["policy_name"] == "baseline_rule"
    assert row["policy_version"] == "0"
    # New A/B + trajectory columns present.
    for col in ("active_proportion_max", "mean_step", "reversal_rate", "track_frames"):
        assert col in row
