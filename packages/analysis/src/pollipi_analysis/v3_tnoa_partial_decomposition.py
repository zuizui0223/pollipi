"""Finite set-valued witnesses for reference-guided partial decomposition."""
from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np


def compatible_signal_set(observation: np.ndarray, nuisance_candidates: Iterable[np.ndarray]) -> tuple[np.ndarray, ...]:
    """Translate a finite nuisance-compatible set into target-compatible signals."""

    y = np.asarray(observation, dtype=np.float64).reshape(-1)
    candidates: list[np.ndarray] = []
    for nuisance in nuisance_candidates:
        n = np.asarray(nuisance, dtype=np.float64).reshape(-1)
        if n.shape != y.shape:
            raise ValueError("all nuisance candidates must match observation dimension")
        candidates.append(y - n)
    if not candidates:
        raise ValueError("nuisance_candidates must be non-empty")
    return tuple(candidates)


def finite_set_diameter(points: Sequence[np.ndarray]) -> float:
    """Euclidean diameter of a finite non-empty point set."""

    if not points:
        raise ValueError("points must be non-empty")
    arrays = [np.asarray(point, dtype=np.float64).reshape(-1) for point in points]
    dimension = arrays[0].shape
    if any(array.shape != dimension for array in arrays):
        raise ValueError("all points must have equal dimension")
    maximum = 0.0
    for index, left in enumerate(arrays):
        for right in arrays[index + 1 :]:
            maximum = max(maximum, float(np.linalg.norm(left - right)))
    return maximum


def true_signal_is_covered(
    observation: np.ndarray,
    true_nuisance: np.ndarray,
    nuisance_candidates: Sequence[np.ndarray],
    *,
    atol: float = 1e-12,
) -> bool:
    """Check the deterministic coverage-transfer implication on a finite set."""

    y = np.asarray(observation, dtype=np.float64).reshape(-1)
    n_true = np.asarray(true_nuisance, dtype=np.float64).reshape(-1)
    if y.shape != n_true.shape:
        raise ValueError("observation and true_nuisance must match")
    nuisance_contains_truth = any(
        np.allclose(np.asarray(candidate, dtype=np.float64).reshape(-1), n_true, atol=atol, rtol=0.0)
        for candidate in nuisance_candidates
    )
    if not nuisance_contains_truth:
        return False
    true_signal = y - n_true
    signal_candidates = compatible_signal_set(y, nuisance_candidates)
    return any(np.allclose(candidate, true_signal, atol=atol, rtol=0.0) for candidate in signal_candidates)
