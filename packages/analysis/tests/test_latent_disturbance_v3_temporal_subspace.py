from __future__ import annotations

import numpy as np

from pollipi_analysis.simulation.latent_disturbance_v3_temporal_subspace import (
    CONDITIONS,
    SCENARIOS,
    T,
    TEMPORAL_RANK,
    evaluate_temporal_subspace,
    generate_temporal_world,
    temporal_subspace_project,
)


def test_reference_is_target_free_and_spatially_noncorresponding() -> None:
    world = generate_temporal_world("target_plus_local_sway", 101)
    assert world.primary_frames.shape == world.reference_frames.shape
    assert np.any(world.target_mask)
    # Reference is a different scene/background and never receives the target layer.
    assert not np.array_equal(world.primary_background, world.reference_background)
    assert not np.array_equal(
        world.primary_frames[world.target_mask] - world.primary_background,
        world.reference_frames[world.target_mask] - world.reference_background,
    )


def test_temporal_projector_preserves_shape_and_reports_energy() -> None:
    world = generate_temporal_world("target_plus_wind", 202)
    corrected, diag = temporal_subspace_project(
        world.primary_frames,
        world.primary_background,
        world.reference_frames,
        world.reference_background,
    )
    assert corrected.shape == world.primary_frames.shape
    assert corrected.shape[0] == T
    assert np.isfinite(corrected).all()
    assert 0.0 <= diag["explained_primary_energy_fraction"] <= 1.0 + 1e-9
    assert 0.0 <= diag["retained_reference_energy_fraction"] <= 1.0 + 1e-9


def test_temporal_benchmark_is_deterministic() -> None:
    a = evaluate_temporal_subspace(n_reps=2, seed=303)
    b = evaluate_temporal_subspace(n_reps=2, seed=303)
    assert a == b
    assert a["sequence_length"] == T
    assert a["temporal_rank"] == TEMPORAL_RANK
    assert set(a["metrics"]) == set(CONDITIONS)
    assert set(a["scenarios"]) == set(SCENARIOS)


def test_temporal_promotion_is_reported_not_asserted() -> None:
    result = evaluate_temporal_subspace(n_reps=1, seed=404)
    criteria = result["promotion_rule"]["criteria"]
    assert result["promotion_rule"]["promoted_to_temporal_reference_candidate"] == all(criteria.values())
