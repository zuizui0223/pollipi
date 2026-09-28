"""Tests for the multi-run within-run random-budget null."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta

import pytest

from pollipi_analysis.policy.three_stage import ThreeStageConfig
from pollipi_analysis.replay.compare import Probe, replay_classified
from pollipi_analysis.replay.joint import (
    JointRun,
    joint_random_budget_baseline,
    load_joint_manifest,
)
from pollipi_analysis.schemas.states import (
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)


SPACING = 5.0


def _joint_run(run_id: str, target_index: int, n: int = 200) -> JointRun:
    states = [NO_ACTIVITY] * n
    states[target_index] = UNCERTAIN_LOCAL_ACTIVITY
    states[target_index + 1] = STRONG_VISITATION_CANDIDATE
    probes = [Probe(i * SPACING, state, False, "image", 0.0) for i, state in enumerate(states)]
    visits = [(target_index * SPACING, target_index * SPACING)]
    cfg = ThreeStageConfig()
    classified = replay_classified(probes, cfg)
    return JointRun(
        run_id=run_id,
        probes=probes,
        visits=visits,
        classified_events=classified,
        low_interval_sec=cfg.low_interval_sec,
        mid_interval_sec=cfg.mid_interval_sec,
        high_interval_sec=cfg.high_interval_sec,
    )


def test_joint_null_detects_repeated_temporal_targeting() -> None:
    runs = [
        _joint_run("run-a", 25),
        _joint_run("run-b", 55),
        _joint_run("run-c", 85),
        _joint_run("run-d", 115),
    ]
    summary = joint_random_budget_baseline(
        runs,
        reps=2_000,
        seed=20260928,
        anchor_first=True,
    )
    assert summary.total_visits == 4
    assert summary.classified_visits_captured == 4
    assert summary.classified_micro_rate == 1.0
    assert summary.classified_macro_rate == 1.0
    assert summary.random_micro_mean < 0.30
    assert summary.random_micro_q95 < 1.0
    assert summary.micro_upper_tail_p_ge_classified < 0.05
    assert summary.macro_upper_tail_p_ge_classified < 0.05


def test_joint_null_is_exactly_invariant_to_manifest_order() -> None:
    runs = [
        _joint_run("run-a", 25),
        _joint_run("run-b", 55),
        _joint_run("run-c", 85),
    ]
    forward = joint_random_budget_baseline(runs, reps=500, seed=77)
    reverse = joint_random_budget_baseline(list(reversed(runs)), reps=500, seed=77)
    assert forward == reverse


def test_joint_micro_and_macro_have_distinct_weighting() -> None:
    # run-a has three visits and captures one; run-b has one visit and captures one.
    # Micro = 2/4 = 0.5; macro = mean(1/3, 1) = 2/3.
    run_a = _joint_run("run-a", 25)
    run_a = JointRun(
        run_id=run_a.run_id,
        probes=run_a.probes,
        visits=[(125.0, 125.0), (250.0, 250.0), (375.0, 375.0)],
        classified_events=run_a.classified_events,
        low_interval_sec=run_a.low_interval_sec,
        mid_interval_sec=run_a.mid_interval_sec,
        high_interval_sec=run_a.high_interval_sec,
    )
    run_b = _joint_run("run-b", 55)
    summary = joint_random_budget_baseline([run_a, run_b], reps=200, seed=4)
    assert summary.classified_micro_rate == pytest.approx(0.5)
    assert summary.classified_macro_rate == pytest.approx(2 / 3)


def _write_probe_log(path, target_index: int, n: int = 40) -> None:
    t0 = datetime(2026, 9, 28, 9, 0, 0)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "probe_timestamp",
                "decision_state",
                "actual_highres_saved",
                "record_kind",
                "video_duration_sec",
            ]
        )
        for i in range(n):
            state = NO_ACTIVITY
            if i == target_index:
                state = UNCERTAIN_LOCAL_ACTIVITY
            elif i == target_index + 1:
                state = STRONG_VISITATION_CANDIDATE
            writer.writerow(
                [
                    (t0 + timedelta(seconds=i * SPACING)).isoformat(timespec="seconds"),
                    state,
                    "False",
                    "image",
                    "",
                ]
            )


def test_manifest_resolves_relative_paths_and_per_run_intervals(tmp_path) -> None:
    log = tmp_path / "run.csv"
    visits = tmp_path / "visits.csv"
    manifest = tmp_path / "manifest.csv"
    _write_probe_log(log, 7)
    visits.write_text("start,end\n35,35\n", encoding="utf-8")
    manifest.write_text(
        "run_id,probe_log,visits_csv,low_interval_sec,mid_interval_sec,high_interval_sec\n"
        "r1,run.csv,visits.csv,40,12,4\n",
        encoding="utf-8",
    )

    runs = load_joint_manifest(manifest)
    assert len(runs) == 1
    run = runs[0]
    assert run.run_id == "r1"
    assert run.low_interval_sec == 40.0
    assert run.mid_interval_sec == 12.0
    assert run.high_interval_sec == 4.0
    assert run.visits == [(35.0, 35.0)]
    assert run.classified_visits_captured == 1


def test_manifest_rejects_duplicate_run_ids(tmp_path) -> None:
    log = tmp_path / "run.csv"
    visits = tmp_path / "visits.csv"
    manifest = tmp_path / "manifest.csv"
    _write_probe_log(log, 7)
    visits.write_text("start,end\n35,35\n", encoding="utf-8")
    manifest.write_text(
        "run_id,probe_log,visits_csv\n"
        "same,run.csv,visits.csv\n"
        "same,run.csv,visits.csv\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate run_id"):
        load_joint_manifest(manifest)
