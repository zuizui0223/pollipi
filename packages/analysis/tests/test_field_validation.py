"""Tests for the frozen paper-level field-validation summary."""
from __future__ import annotations

from pathlib import Path

import pytest

from pollipi_analysis.replay.compare import CaptureEvent, Probe
from pollipi_analysis.replay.field_validation import (
    analyze_field_validation,
    format_field_validation_report,
)
from pollipi_analysis.replay.joint import JointRun
from pollipi_analysis.schemas.states import ENVIRONMENTAL_NOISE, NO_ACTIVITY


def _informative_run(run_id: str, visit_probe_index: int, n: int = 100) -> JointRun:
    # Environmental motion keeps Mode 2 on its 15 s fast schedule. Choose visit
    # times on that schedule but off the 60 s fixed schedule. Mode 3's synthetic
    # observed schedule here contains the first anchor + the activity-targeted still.
    probes = [
        Probe(i * 5.0, ENVIRONMENTAL_NOISE, False, "image", 0.0)
        for i in range(n)
    ]
    visit_time = visit_probe_index * 5.0
    return JointRun(
        run_id=run_id,
        probes=probes,
        visits=[(visit_time, visit_time)],
        classified_events=[
            CaptureEvent(0.0, "image"),
            CaptureEvent(visit_time, "image"),
        ],
        low_interval_sec=60.0,
        mid_interval_sec=15.0,
        high_interval_sec=5.0,
    )


def test_full_positive_pattern_supports_all_frozen_claim_gates() -> None:
    # All target times are multiples of 15 s, but not 60 s.
    runs = [
        _informative_run("a", 27),  # 135 s
        _informative_run("b", 33),  # 165 s
        _informative_run("c", 39),  # 195 s
        _informative_run("d", 45),  # 225 s
        _informative_run("e", 51),  # 255 s
    ]
    summary = analyze_field_validation(
        runs,
        bootstrap_reps=1_000,
        bootstrap_seed=20260928,
        random_reps=2_000,
        random_seed=20260928,
    )
    policies = {p.policy: p for p in summary.policies}

    assert policies["1 fixed"].visit_capture_rate == 0.0
    assert policies["2 any-motion"].visit_capture_rate == 1.0
    assert policies["3 classified"].visit_capture_rate == 1.0
    assert policies["3 classified"].nonvisit_stills_per_hour < policies["2 any-motion"].nonvisit_stills_per_hour

    assert summary.primary_inference_eligible
    assert summary.visit_run_count == 5
    assert summary.cost_run_count == 5
    assert summary.h1_capture_difference.lower > 0.0
    assert summary.h1_supported
    assert summary.h2_capture_difference.lower > -0.05
    assert summary.h2_capture_noninferior
    assert summary.h2_nonvisit_stills_per_hour_difference.upper < 0.0
    assert summary.h2_cost_reduction_supported
    assert summary.h2_supported
    assert summary.random_timing_supported
    assert summary.all_primary_criteria_supported


def test_field_validation_is_invariant_to_run_order() -> None:
    runs = [
        _informative_run("a", 27),
        _informative_run("b", 33),
        _informative_run("c", 39),
    ]
    forward = analyze_field_validation(
        runs,
        bootstrap_reps=300,
        bootstrap_seed=77,
        random_reps=500,
        random_seed=88,
    )
    reverse = analyze_field_validation(
        list(reversed(runs)),
        bootstrap_reps=300,
        bootstrap_seed=77,
        random_reps=500,
        random_seed=88,
    )
    assert forward == reverse


def test_zero_gain_pattern_does_not_pass_h1_or_h2_cost_gate() -> None:
    probes = [Probe(i * 5.0, NO_ACTIVITY, False, "image", 0.0) for i in range(40)]
    # With low interval 30 s, fixed and classified both have t=0,30,60,...
    # Put the visit at 60 s and give classified that same fixed schedule.
    classified = [
        CaptureEvent(float(t), "image")
        for t in range(0, 196, 30)
        if t <= probes[-1].elapsed_sec
    ]
    run = JointRun(
        run_id="neutral",
        probes=probes,
        visits=[(60.0, 60.0)],
        classified_events=classified,
        low_interval_sec=30.0,
        mid_interval_sec=15.0,
        high_interval_sec=5.0,
    )
    summary = analyze_field_validation(
        [run],
        bootstrap_reps=100,
        random_reps=200,
        bootstrap_seed=1,
        random_seed=2,
    )
    assert summary.h1_capture_difference.observed == 0.0
    assert not summary.h1_supported
    assert summary.h2_nonvisit_stills_per_hour_difference.observed == 0.0
    assert not summary.h2_cost_reduction_supported
    assert not summary.h2_supported
    assert not summary.all_primary_criteria_supported


def test_report_and_json_expose_claim_gates() -> None:
    runs = [_informative_run("a", 27), _informative_run("b", 33)]
    summary = analyze_field_validation(
        runs,
        bootstrap_reps=100,
        random_reps=200,
        bootstrap_seed=3,
        random_seed=4,
    )
    report = format_field_validation_report(summary)
    payload = summary.as_dict()

    assert "Frozen claim gates" in report
    assert "H1" in report
    assert "Random equal-budget" in report
    assert payload["analysis_contract"] == "pollipi-field-validation-v1"
    assert payload["noninferiority_margin"] == pytest.approx(0.05)
    assert set(payload["claim_gates"]) == {
        "h1_supported",
        "h2_capture_noninferior",
        "h2_cost_reduction_supported",
        "h2_supported",
        "random_timing_supported",
        "all_primary_criteria_supported",
    }


def test_fewer_than_five_runs_reports_insufficient_evidence() -> None:
    runs = [
        _informative_run("a", 27),
        _informative_run("b", 33),
        _informative_run("c", 39),
        _informative_run("d", 45),
    ]
    summary = analyze_field_validation(
        runs,
        bootstrap_reps=200,
        random_reps=500,
        bootstrap_seed=10,
        random_seed=11,
    )
    # Point estimates can be excellent, but the frozen paper-level gates must
    # remain closed when there are too few independent run clusters.
    assert summary.h1_capture_difference.observed > 0
    assert not summary.primary_inference_eligible
    assert not summary.h1_supported
    assert not summary.h2_capture_noninferior
    assert not summary.h2_cost_reduction_supported
    assert not summary.random_timing_supported
    assert not summary.all_primary_criteria_supported
    assert any("at least 5" in reason for reason in summary.eligibility_reasons)
