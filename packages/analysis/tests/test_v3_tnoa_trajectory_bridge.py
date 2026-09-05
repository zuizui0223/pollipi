from __future__ import annotations

import pytest

pytest.importorskip("tnoa")

from pollipi_analysis.simulation.v3_tnoa_trajectory_bridge import evaluate_trajectory_bridge


def test_small_trajectory_bridge_is_reproducible_and_risk_calibrated() -> None:
    kwargs = dict(
        n_reps=6,
        dev_reps=3,
        seed=20261907,
        alpha=0.05,
        bootstrap_reps=20,
        bootstrap_seed=2026190701,
        pollipi_sha="test",
    )
    first = evaluate_trajectory_bridge(**kwargs)
    second = evaluate_trajectory_bridge(**kwargs)
    assert first == second
    assert first["design"]["target_score"] == "candidate_fraction * path_efficiency * (1 - reversal_rate)"
    for calibration in first["calibration"].values():
        assert max(calibration["target_development_false_support_by_family"].values()) <= 0.05 + 1e-12
        assert calibration["nuisance_development_false_support"] <= 0.05 + 1e-12


def test_trajectory_diagnostics_are_observation_bounded() -> None:
    result = evaluate_trajectory_bridge(
        n_reps=4,
        dev_reps=2,
        seed=20262907,
        bootstrap_reps=10,
        bootstrap_seed=2026290701,
        pollipi_sha="test",
    )
    for arm in result["trajectory_diagnostics"].values():
        for diagnostics in arm.values():
            assert 0.0 <= diagnostics["target_score_mean"] <= 1.0
            assert 0.0 <= diagnostics["candidate_fraction_mean"] <= 1.0
            assert 0.0 <= diagnostics["path_efficiency_mean"] <= 1.0
            assert 0.0 <= diagnostics["reversal_rate_mean"] <= 1.0
            assert 0.0 <= diagnostics["trajectory_points_mean"] <= 9.0
