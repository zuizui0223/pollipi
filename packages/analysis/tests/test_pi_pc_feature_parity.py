"""Phase 1: the Pi runtime and the PC simulation must share one feature space.

The Pi capture loop drives a :class:`pollipi_analysis.track.Tracker` frame by
frame; the PC simulation drives the same sequence through ``run_shadow_mode``.
Both must yield identical per-frame features (including the windowed trajectory
features) and identical decisions. These tests are the regression guard against
the two paths drifting apart again — historically the Pi never populated
``path_efficiency`` / ``mean_step`` / ``reversal_rate`` at all.
"""
from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.pipeline import PipelineConfig
from pollipi_analysis.policy.state_policy import IntervalBounds
from pollipi_analysis.shadow import run_shadow_mode
from pollipi_analysis.simulation.synthetic import simulate_sequence
from pollipi_analysis.track import Tracker

BOUNDS = IntervalBounds(baseline_interval_sec=60, min_interval_sec=10, max_interval_sec=180)


def _pi_style_decisions(frames, *, config=None):
    """Reproduce exactly what the Pi capture loop does: a Tracker fed frame pairs.

    The Pi compares each scheduled frame against the previous scheduled frame,
    skipping the first (reference) frame — identical pairing to run_shadow_mode.
    """
    tracker = Tracker(config=config or PipelineConfig())
    decisions = []
    previous = None
    for frame in frames:
        if previous is None:
            previous = frame
            continue
        decisions.append(tracker.observe(frame, previous))
        previous = frame
    return decisions


@pytest.mark.parametrize(
    "scenario", ["target_traverse", "local_sway", "moving_shadow", "broad_wind", "quiet"]
)
def test_pi_tracker_matches_pc_shadow_runner(scenario) -> None:
    frames = simulate_sequence(scenario, n_frames=8, seed=7)

    pi = _pi_style_decisions(frames)
    pc = run_shadow_mode(frames, bounds=BOUNDS)

    assert len(pi) == len(pc)
    for pi_decision, pc_record in zip(pi, pc):
        pc_decision = pc_record.decision
        assert pi_decision.state == pc_decision.state
        assert pi_decision.reason == pc_decision.reason
        # Full feature vector must be byte-for-byte identical across the two paths.
        assert pi_decision.features.to_dict() == pc_decision.features.to_dict()


def test_pi_path_populates_trajectory_features() -> None:
    # Regression guard: the Pi path used to leave these None forever.
    frames = simulate_sequence("target_traverse", n_frames=8, seed=7)
    decisions = _pi_style_decisions(frames)
    last = decisions[-1].features
    assert last.track_frames >= 2
    assert last.path_efficiency is not None
    assert last.mean_step is not None
    assert last.reversal_rate is not None


def test_tracker_carries_previous_state_for_persistence() -> None:
    frames = simulate_sequence("target_traverse", n_frames=6, seed=7)
    tracker = Tracker()
    previous = frames[0]
    # After several observations the centroid window has grown and persistence is
    # computed against the prior frame's active cells (non-trivial state carried).
    seen_frames = 0
    for frame in frames[1:]:
        tracker.observe(frame, previous)
        previous = frame
        seen_frames += 1
    assert tracker.track_frames == min(seen_frames, tracker.track_window)
