"""Phase 2: the objective is power-efficiency, not detection accuracy.

These assert the device-level properties the objective must reward: HIGH during
genuine insect windows, LOW (low power) the rest of the time, and as few
false-HIGH ticks as possible on wind/shadow/sway.
"""
from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.policy.two_stage import TwoStageConfig
from pollipi_analysis.simulation.power_search import (
    default_timelines,
    run_power_search,
    select_power_policy,
)
from pollipi_analysis.simulation.timeline import (
    TimelineSegment,
    generate_timeline,
    simulate_power,
)

CFG = TwoStageConfig(low_rate_sec=30.0, high_rate_sec=5.0, high_hold_sec=60.0)
BASE = CFG.high_rate_sec


def test_quiet_only_timeline_stays_low_power_and_no_false_high() -> None:
    frames, truth = generate_timeline([TimelineSegment("quiet", 40)], seed=3)
    m = simulate_power(frames, truth, base_rate_sec=BASE, controller_config=CFG)
    assert m.insect_ticks == 0
    assert m.false_high_ticks == 0
    # On a quiet timeline almost every tick is skipped (LOW): far fewer captures
    # than ticks.
    assert m.captures < m.n_ticks / 3


def test_insect_window_is_covered_at_high() -> None:
    frames, truth = generate_timeline(
        [TimelineSegment("quiet", 10), TimelineSegment("insect", 12), TimelineSegment("quiet", 10)],
        seed=5,
    )
    m = simulate_power(frames, truth, base_rate_sec=BASE, controller_config=CFG)
    assert m.insect_ticks == 12
    # The directed traverse should pull the controller into HIGH for most of it.
    assert m.coverage > 0.5


def test_false_high_rate_low_on_pure_noise() -> None:
    frames, truth = generate_timeline(
        [
            TimelineSegment("broad_wind", 14),
            TimelineSegment("moving_shadow", 14),
            TimelineSegment("local_sway", 14),
        ],
        seed=9,
    )
    m = simulate_power(frames, truth, base_rate_sec=BASE, controller_config=CFG)
    assert m.insect_ticks == 0
    # Wind/shadow/sway should rarely (ideally never) be worth HIGH.
    assert m.false_high_rate < 0.25


def test_power_search_selects_a_config_and_reports_power_metrics() -> None:
    rows = run_power_search(seed=7)
    assert rows
    for r in rows:
        assert set(("cost", "captures_per_hour", "false_high_rate", "coverage")) <= set(r)
    best = select_power_policy(rows)
    # The chosen policy must not be the worst on cost.
    assert best["cost"] <= max(r["cost"] for r in rows)


def test_default_timelines_contain_insect_and_noise() -> None:
    timelines = default_timelines(seed=7)
    assert timelines
    for _frames, truth in timelines:
        assert any(truth) and not all(truth)
