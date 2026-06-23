from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.policy.state_policy import IntervalBounds
from pollipi_analysis.schemas.shadow import SHADOW_LOG_COLUMNS
from pollipi_analysis.schemas.states import STRONG_VISITATION_CANDIDATE
from pollipi_analysis.shadow import run_shadow_mode
from pollipi_analysis.simulation.synthetic import simulate_sequence

BOUNDS = IntervalBounds(baseline_interval_sec=60, min_interval_sec=10, max_interval_sec=180)


def _states(scenario: str):
    frames = simulate_sequence(scenario, n_frames=6, seed=7)
    records = run_shadow_mode(frames, bounds=BOUNDS, device_id="test")
    return records


def test_shadow_mode_never_marks_decisions_as_applied() -> None:
    for record in _states("target_traverse"):
        assert record.applied is False
        assert record.current_interval_sec == 60  # real interval unchanged


def test_target_traverse_produces_a_strong_candidate_and_shortens_would_be_interval() -> None:
    records = _states("target_traverse")
    strong = [r for r in records if r.decision.state == STRONG_VISITATION_CANDIDATE]
    assert strong, "directed traverse should yield at least one strong candidate"
    assert min(r.would_be_next_interval_sec for r in strong) < 60


def test_oscillation_mechanism_fires_and_directed_motion_is_discriminated() -> None:
    # Honest limitation (Issue #14 synthetic conclusion): a target-like object
    # swaying back and forth is hard to reject frame-to-frame. We assert only the
    # robust facts: (1) the path-efficiency oscillation override fires at least
    # once on sustained sway, and (2) a directed traverse is strong on strictly
    # more frames than the sway -- i.e. path efficiency discriminates them.
    sway = run_shadow_mode(
        simulate_sequence("local_sway", n_frames=8, seed=7), bounds=BOUNDS
    )
    traverse = run_shadow_mode(
        simulate_sequence("target_traverse", n_frames=8, seed=7), bounds=BOUNDS
    )
    assert any(r.decision.reason == "low_path_efficiency_oscillation" for r in sway)
    sway_strong = sum(r.decision.state == STRONG_VISITATION_CANDIDATE for r in sway)
    traverse_strong = sum(r.decision.state == STRONG_VISITATION_CANDIDATE for r in traverse)
    assert traverse_strong > sway_strong


def test_quiet_sequence_keeps_interval_at_or_above_baseline() -> None:
    records = _states("quiet")
    assert all(r.would_be_next_interval_sec >= 60 for r in records)
    assert all(r.decision.state != STRONG_VISITATION_CANDIDATE for r in records)


def test_shadow_log_row_matches_the_documented_contract() -> None:
    record = _states("target_traverse")[0]
    row = record.to_row()
    assert set(row.keys()) == set(SHADOW_LOG_COLUMNS)
    # The contract must not leak a motion-image path: shadow mode stores no frames.
    assert not any("image" in key or "path_to" in key for key in row)
    assert row["applied"] is False


def test_path_efficiency_is_populated_over_the_track_window() -> None:
    records = _states("target_traverse")
    assert any(r.decision.features.path_efficiency is not None for r in records)
