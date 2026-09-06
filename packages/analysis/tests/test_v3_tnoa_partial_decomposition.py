from __future__ import annotations

import numpy as np

from pollipi_analysis.v3_tnoa_partial_decomposition import (
    compatible_signal_set,
    finite_set_diameter,
    true_signal_is_covered,
)


def test_signal_compatible_set_is_translated_nuisance_set() -> None:
    y = np.array([5.0, 2.0])
    nuisance = (
        np.array([1.0, 0.0]),
        np.array([2.0, 1.0]),
        np.array([3.0, -1.0]),
    )
    signals = compatible_signal_set(y, nuisance)
    np.testing.assert_allclose(signals[0], np.array([4.0, 2.0]))
    np.testing.assert_allclose(signals[1], np.array([3.0, 1.0]))
    np.testing.assert_allclose(signals[2], np.array([2.0, 3.0]))


def test_target_set_diameter_equals_nuisance_set_diameter() -> None:
    y = np.array([10.0, -4.0, 2.0])
    nuisance = (
        np.array([0.0, 0.0, 0.0]),
        np.array([1.0, 2.0, 0.0]),
        np.array([-1.0, 1.0, 3.0]),
    )
    signals = compatible_signal_set(y, nuisance)
    np.testing.assert_allclose(finite_set_diameter(signals), finite_set_diameter(nuisance))


def test_reference_refinement_contracts_signal_compatible_set() -> None:
    y = np.array([5.0, 5.0])
    nuisance_coarse = (
        np.array([0.0, 0.0]),
        np.array([1.0, 0.0]),
        np.array([2.0, 0.0]),
    )
    nuisance_refined = nuisance_coarse[:2]
    signals_coarse = compatible_signal_set(y, nuisance_coarse)
    signals_refined = compatible_signal_set(y, nuisance_refined)
    assert finite_set_diameter(signals_refined) < finite_set_diameter(signals_coarse)


def test_true_nuisance_membership_transfers_to_true_signal_membership() -> None:
    signal = np.array([2.0, -1.0])
    true_nuisance = np.array([3.0, 4.0])
    y = signal + true_nuisance
    nuisance_candidates = (
        np.array([0.0, 0.0]),
        true_nuisance,
        np.array([5.0, 5.0]),
    )
    assert true_signal_is_covered(y, true_nuisance, nuisance_candidates)


def test_exact_reference_point_identifies_signal() -> None:
    signal = np.array([2.0, -1.0])
    nuisance = np.array([3.0, 4.0])
    y = signal + nuisance
    compatible = compatible_signal_set(y, (nuisance,))
    assert len(compatible) == 1
    np.testing.assert_allclose(compatible[0], signal)
    assert finite_set_diameter(compatible) == 0.0
