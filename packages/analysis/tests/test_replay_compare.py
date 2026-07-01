"""Counterfactual ①②③ replay over a recorded probe log.

The study claim under test: on the SAME recorded decision sequence, ③ wastes
fewer captures on environmental noise than ②, and escalates on a real strong
candidate where a slow fixed timelapse would not — i.e. ③ sits between ①'s
misses and ②'s waste.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta

import pytest

from pollipi_analysis.replay.compare import (
    CostModel,
    Probe,
    compare,
    load_probe_log,
    load_visits,
    read_run_start,
    replay_any_motion,
    replay_classified,
    replay_fixed,
    replay_video,
)
from pollipi_analysis.policy.three_stage import ThreeStageConfig
from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)

PROBE_SPACING = 5.0


def _probes(states: list[str], spacing: float = PROBE_SPACING) -> list[Probe]:
    return [Probe(i * spacing, s, False, "image", 0.0) for i, s in enumerate(states)]


def test_fixed_captures_at_its_interval() -> None:
    # 0..120 s at 5 s probes, all quiet -> ① at 30 s captures t=0,30,60,90,120.
    probes = _probes([NO_ACTIVITY] * 25)
    events = replay_fixed(probes, 30.0)
    assert [e.time_sec for e in events] == [0.0, 30.0, 60.0, 90.0, 120.0]


def test_any_motion_wastes_captures_on_environmental_noise() -> None:
    # Constant wind/shadow -> ② treats it as motion (MID/15 s); ③ treats
    # environmental_noise as quiet (LOW/30 s). This is the core wasted-capture claim.
    probes = _probes([ENVIRONMENTAL_NOISE] * 25)  # 0..120 s
    base = ThreeStageConfig()
    two = replay_any_motion(probes, base)
    three = replay_classified(probes, base)
    fixed = replay_fixed(probes, base.low_interval_sec)
    stills2 = sum(1 for e in two if e.kind == "image")
    stills3 = sum(1 for e in three if e.kind == "image")
    stills1 = sum(1 for e in fixed if e.kind == "image")
    assert stills2 > stills3          # ② wastes on noise
    assert stills3 == stills1         # ③ ignores noise -> same as fixed baseline
    assert all(e.kind != "video" for e in three)  # noise never fires a clip


def test_video_fires_on_sustained_strong_but_classified_stills_does_not() -> None:
    # Two consecutive local probes incl. strong -> ④ fires one clip; ③ (stills)
    # escalates to a fast still burst instead, never a clip.
    seq = [NO_ACTIVITY, UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE] + [NO_ACTIVITY] * 5
    probes = _probes(seq)
    four = replay_video(probes, ThreeStageConfig())
    three = replay_classified(probes, ThreeStageConfig())
    assert sum(1 for e in four if e.kind == "video") == 1
    assert all(e.kind != "video" for e in three)  # ③ is stills-only


def test_visit_capture_rate_rewards_escalation() -> None:
    # A short visit spanning one 5 s slot at t=25..30. ① at 60 s misses it;
    # ③ escalates and captures it.
    seq = [NO_ACTIVITY] * 5 + [UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE] + [NO_ACTIVITY] * 5
    probes = _probes(seq)
    visits = [(25.0, 35.0)]
    cmp = compare(probes, fixed_interval_sec=60.0, visits=visits)
    by_name = {r.name: r for r in cmp.results}
    assert by_name["1 fixed"].visit_capture_rate == 0.0
    assert by_name["3 classified"].visit_capture_rate == 1.0   # ③ stills escalates
    assert by_name["4 video"].visit_capture_rate == 1.0        # ④ also captures


def test_storage_proxy_tracks_stills_and_video() -> None:
    probes = _probes([NO_ACTIVITY] * 7)  # ① 30 s over 0..30 -> 2 stills
    cost = CostModel(still_bytes=500_000, video_bitrate_bits=6_000_000)
    cmp = compare(probes, fixed_interval_sec=30.0, cost=cost)
    fixed = next(r for r in cmp.results if r.name == "1 fixed")
    assert fixed.stills == 2
    assert fixed.est_storage_mb == pytest.approx(2 * 500_000 / 1e6)


def test_round_trip_through_csv_and_actual_cross_check(tmp_path) -> None:
    # Write a minimal v2-style log; the "actual (logged)" policy reflects the rows.
    path = tmp_path / "adaptive_probe_shadow_v2_run.csv"
    t0 = datetime(2026, 7, 4, 9, 0, 0)
    rows = [
        # ts, state, actual_saved, record_kind, video_dur
        (t0, NO_ACTIVITY, "True", "image", ""),
        (t0 + timedelta(seconds=5), ENVIRONMENTAL_NOISE, "False", "image", ""),
        (t0 + timedelta(seconds=10), STRONG_VISITATION_CANDIDATE, "False", "video", "30.000"),
    ]
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["probe_timestamp", "decision_state", "actual_highres_saved",
                    "record_kind", "video_duration_sec"])
        for ts, st, saved, kind, vdur in rows:
            w.writerow([ts.isoformat(timespec="seconds"), st, saved, kind, vdur])

    probes = load_probe_log(path)
    assert [p.elapsed_sec for p in probes] == [0.0, 5.0, 10.0]
    cmp = compare(probes)
    actual = next(r for r in cmp.results if r.name == "actual(log)")
    assert actual.stills == 1 and actual.video_clips == 1 and actual.video_seconds == 30.0

    # ISO visit annotations resolve against the run start.
    vpath = tmp_path / "visits.csv"
    vpath.write_text("start,end\n2026-07-04T09:00:08,2026-07-04T09:00:12\n", encoding="utf-8")
    visits = load_visits(vpath, read_run_start(path))
    assert visits == [(8.0, 12.0)]
