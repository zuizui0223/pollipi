from __future__ import annotations

import numpy as np

from pollipi_analysis.simulation.latent_disturbance_v2 import (
    REFERENCE_CONDITIONS,
    SCENARIOS,
    evaluate,
    generate_world,
    project_reference,
)


def test_correct_reference_is_target_free_for_target_only() -> None:
    world = generate_world("target_only", 11)
    assert np.allclose(world.correct_reference, world.background)
    assert np.max(np.abs(world.primary - world.background)) > 0


def test_correct_reference_projection_removes_shared_nuisance_without_labels() -> None:
    world = generate_world("target_plus_wind", 17)
    corrected, alpha = project_reference(world.primary, world.background, world.correct_reference)
    raw_energy = float(np.mean(np.abs(world.primary - world.background)))
    corrected_energy = float(np.mean(np.abs(corrected - world.background)))
    assert 0.0 <= alpha <= 1.5
    assert corrected_energy < raw_energy


def test_corrupted_reference_breaks_exact_event_level_coupling() -> None:
    world = generate_world("target_plus_shadow", 23)
    correct_delta = world.correct_reference - world.background
    corrupt_delta = world.corrupted_reference - world.background
    assert not np.array_equal(correct_delta, corrupt_delta)


def test_benchmark_is_deterministic_and_reports_all_conditions() -> None:
    a = evaluate(n_reps=2, seed=101)
    b = evaluate(n_reps=2, seed=101)
    assert a == b
    assert set(a["metrics"]) == set(REFERENCE_CONDITIONS)
    for condition in REFERENCE_CONDITIONS:
        rates = a["metrics"][condition]["per_scenario_local_candidate_rate"]
        assert set(rates) == set(SCENARIOS)
        assert all(0.0 <= value <= 1.0 for value in rates.values())


def test_promotion_rule_is_reported_not_asserted() -> None:
    result = evaluate(n_reps=1, seed=7)
    criteria = result["promotion_rule"]["criteria"]
    assert set(criteria) == {
        "mixed_target_recall_gain_ge_0_10",
        "nuisance_fpr_not_worse",
        "balanced_utility_gain_vs_corrupted_ge_0_08",
        "target_only_recall_loss_le_0_05",
    }
    assert result["promotion_rule"]["promoted_to_candidate_method"] == all(criteria.values())
