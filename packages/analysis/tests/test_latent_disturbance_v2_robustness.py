from __future__ import annotations

import numpy as np

from pollipi_analysis.simulation.latent_disturbance_v2 import generate_world
from pollipi_analysis.simulation.latent_disturbance_v2_robustness import (
    ROBUSTNESS_CONDITIONS,
    degraded_reference,
    evaluate_reference_robustness,
)


def test_degraded_reference_shapes_and_no_reference() -> None:
    world = generate_world("target_plus_wind", 31)
    for i, condition in enumerate(ROBUSTNESS_CONDITIONS):
        ref = degraded_reference(world, condition, 100 + i)
        if condition == "no_reference":
            assert ref is None
        else:
            assert ref is not None
            assert ref.shape == world.background.shape
            assert np.isfinite(ref).all()


def test_target_only_degraded_reference_does_not_copy_primary_target() -> None:
    world = generate_world("target_only", 41)
    primary_delta = world.primary - world.background
    assert np.max(np.abs(primary_delta)) > 0
    for i, condition in enumerate(("gain_noise_reference", "shift2_reference", "partial75_reference")):
        ref = degraded_reference(world, condition, 200 + i)
        assert ref is not None
        reference_delta = ref - world.background
        # With no nuisance, degraded reference may contain sensor noise but never the
        # exact target layer from the primary channel.
        assert not np.array_equal(reference_delta, primary_delta)


def test_robustness_benchmark_is_deterministic() -> None:
    a = evaluate_reference_robustness(n_reps=2, seed=303)
    b = evaluate_reference_robustness(n_reps=2, seed=303)
    assert a == b
    assert set(a["metrics"]) == set(ROBUSTNESS_CONDITIONS)


def test_robustness_promotion_is_reported_not_asserted() -> None:
    result = evaluate_reference_robustness(n_reps=1, seed=17)
    criteria = result["promotion_rule"]["criteria"]
    assert result["promotion_rule"]["promoted_to_reference_robust_candidate"] == all(criteria.values())
