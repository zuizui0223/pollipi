from __future__ import annotations

import numpy as np

from pollipi_analysis.simulation.latent_disturbance_v2 import generate_world
from pollipi_analysis.simulation.latent_disturbance_v2_oracle_shift import (
    BORDER_WIDTH,
    border_excess,
    evaluate_oracle_shift,
    oracle_restore_reference,
)
from pollipi_analysis.simulation.latent_disturbance_v2_robustness import degraded_reference
from pollipi_analysis.simulation.latent_disturbance_v2_shift_diagnostic import injected_shift_from_seed


def test_oracle_restore_keeps_shape_and_is_finite() -> None:
    world = generate_world("target_plus_wind", 101)
    seed = 404
    ref = degraded_reference(world, "shift2_reference", seed)
    assert ref is not None
    restored = oracle_restore_reference(world.background, ref, injected_shift_from_seed(seed))
    assert restored.shape == world.background.shape
    assert np.isfinite(restored).all()


def test_border_excess_zero_for_clean_background() -> None:
    world = generate_world("wind_only", 202)
    assert border_excess(world.background, world.background, BORDER_WIDTH) == 0.0


def test_oracle_diagnostic_is_deterministic() -> None:
    a = evaluate_oracle_shift(n_reps=2, seed=505)
    b = evaluate_oracle_shift(n_reps=2, seed=505)
    assert a == b
    assert a["border_width_px"] == BORDER_WIDTH


def test_oracle_diagnostic_reports_all_conditions() -> None:
    result = evaluate_oracle_shift(n_reps=1, seed=606)
    assert set(result["metrics"]) == {
        "exact_reference",
        "oracle_shift_reference",
        "estimated_shift_v2_1",
        "shift2_unaligned",
        "no_reference",
    }
