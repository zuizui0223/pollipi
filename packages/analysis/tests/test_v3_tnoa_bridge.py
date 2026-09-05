from __future__ import annotations

import pytest

pytest.importorskip("tnoa")

from pollipi_analysis.simulation.v3_tnoa_bridge import evaluate_bridge


def test_small_bridge_is_reproducible_and_calibration_respects_alpha() -> None:
    kwargs = dict(
        n_reps=6,
        dev_reps=3,
        seed=20261906,
        alpha=0.05,
        bootstrap_reps=25,
        bootstrap_seed=2026190601,
        pollipi_sha="test",
    )
    first = evaluate_bridge(**kwargs)
    second = evaluate_bridge(**kwargs)

    assert first == second
    assert first["design"]["development_reps"] == 3
    assert first["design"]["heldout_reps"] == 3

    for arm, calibration in first["calibration"].items():
        assert arm in {"raw", "matched_v3", "time_broken_v3"}
        assert max(calibration["target_development_false_support_by_family"].values()) <= 0.05 + 1e-12
        assert calibration["nuisance_development_false_support"] <= 0.05 + 1e-12


def test_bridge_uses_dynamic_tnoa_semantics_without_baseline_shortcut() -> None:
    result = evaluate_bridge(
        n_reps=4,
        dev_reps=2,
        seed=20262906,
        bootstrap_reps=10,
        bootstrap_seed=2026290601,
        pollipi_sha="test",
    )

    assert "target_only" in result["design"]["scenarios"]
    assert "wind_only" in result["design"]["scenarios"]
    assert result["schema"] == "pollipi-v3-tnoa-synthetic-bridge-v1"
    for metrics in result["heldout_metrics"].values():
        assert 0.0 <= metrics["safe_unique_coverage"] <= 1.0
        assert 0.0 <= metrics["pooled_false_certainty_rate"] <= 1.0
        assert 0.0 <= metrics["overlap_abstention_rate"] <= 1.0
