from __future__ import annotations

from pollipi_analysis.simulation.latent_disturbance_v2 import generate_world
from pollipi_analysis.simulation.latent_disturbance_v2_robustness import degraded_reference
from pollipi_analysis.simulation.latent_disturbance_v2_shift_diagnostic import (
    evaluate_shift_identifiability,
    injected_shift_from_seed,
    rank_alignment_candidates,
)


def test_injected_shift_is_nonzero_and_bounded() -> None:
    dy, dx = injected_shift_from_seed(123)
    assert (dy, dx) != (0, 0)
    assert -2 <= dy <= 2
    assert -2 <= dx <= 2


def test_alignment_candidate_ranking_has_all_25_shifts() -> None:
    world = generate_world("target_plus_wind", 91)
    ref = degraded_reference(world, "shift2_reference", 303)
    assert ref is not None
    rows = rank_alignment_candidates(world.primary, world.background, ref)
    assert len(rows) == 25
    assert rows[0]["loss"] <= rows[1]["loss"]


def test_shift_diagnostic_is_deterministic() -> None:
    a = evaluate_shift_identifiability(n_reps=2, seed=707)
    b = evaluate_shift_identifiability(n_reps=2, seed=707)
    assert a == b
    assert a["overall"]["n"] == 16


def test_diagnostic_excludes_target_only() -> None:
    result = evaluate_shift_identifiability(n_reps=1, seed=808)
    assert "target_only" not in result["scenarios"]
