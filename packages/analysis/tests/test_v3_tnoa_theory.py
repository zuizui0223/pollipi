from __future__ import annotations

import numpy as np

from pollipi_analysis.v3_tnoa_theory import (
    additive_alternative,
    adversarial_target_for_projector,
    augment_representation,
    capture_fraction,
    compatible_fiber,
    identified_set,
    orthogonal_projector,
    projection_tradeoff,
    refinement_is_subset,
)


def test_reference_refinement_shrinks_compatible_worlds_and_identified_set() -> None:
    worlds = (
        {"id": "a", "y": 0, "r": 0, "theta": 0},
        {"id": "b", "y": 0, "r": 1, "theta": 1},
        {"id": "c", "y": 1, "r": 0, "theta": 2},
    )
    y = lambda w: w["y"]
    yr = lambda w: (w["y"], w["r"])
    theta = lambda w: w["theta"]

    assert refinement_is_subset(worlds, y, yr, worlds[0])
    assert set(compatible_fiber(worlds, y, 0)) == {worlds[0], worlds[1]}
    assert set(compatible_fiber(worlds, yr, (0, 0))) == {worlds[0]}
    assert identified_set(worlds, y, 0, theta) == frozenset({0, 1})
    assert identified_set(worlds, yr, (0, 0), theta) == frozenset({0})


def test_deterministic_coarsening_expands_compatible_worlds() -> None:
    worlds = (
        {"e": "T", "binary": 1, "theta": "target-only"},
        {"e": "U-overlap", "binary": 1, "theta": "target+nuisance"},
        {"e": "N", "binary": 0, "theta": "nuisance-only"},
    )
    rich = lambda w: w["e"]
    coarse = lambda w: w["binary"]
    theta = lambda w: w["theta"]

    assert identified_set(worlds, rich, "T", theta) == frozenset({"target-only"})
    assert identified_set(worlds, coarse, 1, theta) == frozenset({"target-only", "target+nuisance"})


def test_primary_only_additive_decomposition_has_observationally_equivalent_alternative() -> None:
    signal = np.array([1.0, 2.0, -1.0])
    nuisance = np.array([0.5, -1.0, 3.0])
    delta = np.array([2.0, 0.25, -0.5])
    signal2, nuisance2 = additive_alternative(signal, nuisance, delta)
    np.testing.assert_allclose(signal + nuisance, signal2 + nuisance2)
    assert not np.allclose(signal, signal2)
    assert not np.allclose(nuisance, nuisance2)


def test_projection_improves_energy_ratio_exactly_when_nuisance_capture_exceeds_target_capture() -> None:
    projector = orthogonal_projector(np.array([[1.0], [0.0]]))
    target = np.array([1.0, 3.0])
    nuisance = np.array([3.0, 1.0])
    tradeoff = projection_tradeoff(projector, target, nuisance)

    assert tradeoff.nuisance_capture > tradeoff.target_capture
    assert tradeoff.snr_gain_factor > 1.0
    np.testing.assert_allclose(
        tradeoff.snr_gain_factor,
        (1.0 - tradeoff.target_capture) / (1.0 - tradeoff.nuisance_capture),
    )


def test_projection_harms_target_when_target_capture_exceeds_nuisance_capture() -> None:
    projector = orthogonal_projector(np.array([[1.0], [0.0]]))
    target = np.array([3.0, 1.0])
    nuisance = np.array([1.0, 3.0])
    tradeoff = projection_tradeoff(projector, target, nuisance)
    assert tradeoff.target_capture > tradeoff.nuisance_capture
    assert tradeoff.snr_gain_factor < 1.0


def test_nonzero_reference_projector_has_target_that_is_erased() -> None:
    projector = orthogonal_projector(np.array([[1.0], [1.0], [0.0]]))
    target = adversarial_target_for_projector(projector)
    assert capture_fraction(projector, target) > 1.0 - 1e-10
    residual = target - projector @ target
    assert np.linalg.norm(residual) < 1e-10


def test_augmented_representation_retains_raw_exactly() -> None:
    raw = np.array([2.0, -1.0, 4.0])
    reference = np.array([[1.0, 0.0], [0.0, 1.0]])
    projector = orthogonal_projector(np.array([[1.0], [0.0], [0.0]]))
    augmented = augment_representation(raw, reference, projector)

    np.testing.assert_array_equal(augmented.raw, raw)
    np.testing.assert_allclose(augmented.explained + augmented.residual, raw)
    np.testing.assert_array_equal(augmented.reference, reference)
