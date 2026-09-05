from __future__ import annotations

import numpy as np

from pollipi_analysis.simulation.latent_disturbance_v2 import generate_world
from pollipi_analysis.simulation.latent_disturbance_v2_alignment import (
    MAX_SHIFT,
    TRIM_FRACTION,
    align_and_project,
    evaluate_alignment,
)
from pollipi_analysis.simulation.latent_disturbance_v2_robustness import degraded_reference


def test_alignment_search_stays_within_frozen_bounds() -> None:
    world = generate_world("target_plus_wind", 55)
    ref = degraded_reference(world, "shift2_reference", 101)
    assert ref is not None
    frame, alpha, (dy, dx), loss = align_and_project(world.primary, world.background, ref)
    assert frame.shape == world.primary.shape
    assert 0.0 <= alpha <= 1.5
    assert -MAX_SHIFT <= dy <= MAX_SHIFT
    assert -MAX_SHIFT <= dx <= MAX_SHIFT
    assert np.isfinite(loss)


def test_alignment_is_label_free_and_preserves_target_only_shape() -> None:
    world = generate_world("target_only", 77)
    ref = degraded_reference(world, "shift2_reference", 202)
    assert ref is not None
    frame, _, _, _ = align_and_project(world.primary, world.background, ref)
    assert frame.shape == world.primary.shape
    assert np.isfinite(frame).all()


def test_alignment_benchmark_is_deterministic() -> None:
    a = evaluate_alignment(n_reps=2, seed=909)
    b = evaluate_alignment(n_reps=2, seed=909)
    assert a == b
    assert a["max_shift_px"] == MAX_SHIFT
    assert a["trim_fraction"] == TRIM_FRACTION


def test_alignment_promotion_is_reported_not_asserted() -> None:
    result = evaluate_alignment(n_reps=1, seed=19)
    criteria = result["promotion_rule"]["criteria"]
    assert result["promotion_rule"]["promoted_to_simulation_robust_field_shadow_candidate"] == all(criteria.values())
