"""Executable witnesses for the V3–TNOA information-order theory core.

The functions in this module are deliberately generic.  They do not implement a
camera pipeline or a learned observer.  They make the structural propositions in
``docs/V3_TNOA_THEORY_CORE.md`` executable on finite worlds and finite-dimensional
linear spaces.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Sequence, TypeVar

import numpy as np

W = TypeVar("W")
X = TypeVar("X", bound=Hashable)
T = TypeVar("T", bound=Hashable)


def compatible_fiber(
    worlds: Iterable[W], observation: Callable[[W], X], observed_value: X
) -> tuple[W, ...]:
    """Return all latent worlds compatible with one observed value."""

    return tuple(world for world in worlds if observation(world) == observed_value)


def identified_set(
    worlds: Iterable[W],
    observation: Callable[[W], X],
    observed_value: X,
    estimand: Callable[[W], T],
) -> frozenset[T]:
    """Return the finite identified set for ``estimand`` under an observation."""

    return frozenset(estimand(world) for world in compatible_fiber(worlds, observation, observed_value))


def refinement_is_subset(
    worlds: Sequence[W],
    coarse_observation: Callable[[W], X],
    fine_observation: Callable[[W], Hashable],
    world: W,
) -> bool:
    """Check the compatible-fiber inclusion for a realized world."""

    coarse_value = coarse_observation(world)
    fine_value = fine_observation(world)
    coarse = set(compatible_fiber(worlds, coarse_observation, coarse_value))
    fine = set(compatible_fiber(worlds, fine_observation, fine_value))
    return fine.issubset(coarse)


def additive_alternative(
    signal: np.ndarray, nuisance: np.ndarray, delta: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Construct an observationally equivalent additive decomposition."""

    s = np.asarray(signal, dtype=np.float64)
    n = np.asarray(nuisance, dtype=np.float64)
    d = np.asarray(delta, dtype=np.float64)
    if s.shape != n.shape or s.shape != d.shape:
        raise ValueError("signal, nuisance and delta must have identical shapes")
    return s + d, n - d


def orthogonal_projector(basis: np.ndarray, *, atol: float = 1e-12) -> np.ndarray:
    """Return the orthogonal projector onto the column space of ``basis``."""

    matrix = np.asarray(basis, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError("basis must be a two-dimensional matrix")
    if matrix.shape[0] == 0:
        raise ValueError("basis must have positive ambient dimension")
    if not np.isfinite(matrix).all():
        raise ValueError("basis contains non-finite values")

    if matrix.shape[1] == 0 or np.linalg.norm(matrix) <= atol:
        return np.zeros((matrix.shape[0], matrix.shape[0]), dtype=np.float64)

    u, singular_values, _ = np.linalg.svd(matrix, full_matrices=False)
    if singular_values.size == 0:
        return np.zeros((matrix.shape[0], matrix.shape[0]), dtype=np.float64)
    threshold = max(atol, atol * float(singular_values[0]))
    rank = int(np.count_nonzero(singular_values > threshold))
    if rank == 0:
        return np.zeros((matrix.shape[0], matrix.shape[0]), dtype=np.float64)
    q = u[:, :rank]
    return q @ q.T


def capture_fraction(projector: np.ndarray, vector: np.ndarray) -> float:
    """Fraction of vector energy captured by an orthogonal projector."""

    p = np.asarray(projector, dtype=np.float64)
    x = np.asarray(vector, dtype=np.float64).reshape(-1)
    if p.shape != (x.size, x.size):
        raise ValueError("projector shape does not match vector dimension")
    energy = float(x @ x)
    if energy <= 0.0:
        raise ValueError("capture fraction is undefined for a zero vector")
    projected = p @ x
    return float(projected @ projected) / energy


@dataclass(frozen=True)
class ProjectionTradeoff:
    target_capture: float
    nuisance_capture: float
    target_residual_fraction: float
    nuisance_residual_fraction: float
    snr_gain_factor: float


def projection_tradeoff(
    projector: np.ndarray, target: np.ndarray, nuisance: np.ndarray
) -> ProjectionTradeoff:
    """Evaluate the exact energy-ratio tradeoff for one orthogonal projection."""

    a_target = capture_fraction(projector, target)
    a_nuisance = capture_fraction(projector, nuisance)
    target_residual = max(0.0, 1.0 - a_target)
    nuisance_residual = max(0.0, 1.0 - a_nuisance)
    if nuisance_residual == 0.0:
        gain = float("inf") if target_residual > 0.0 else float("nan")
    else:
        gain = target_residual / nuisance_residual
    return ProjectionTradeoff(
        target_capture=a_target,
        nuisance_capture=a_nuisance,
        target_residual_fraction=target_residual,
        nuisance_residual_fraction=nuisance_residual,
        snr_gain_factor=gain,
    )


def decompose(projector: np.ndarray, observation: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return reference-explained and residual components without discarding raw."""

    p = np.asarray(projector, dtype=np.float64)
    y = np.asarray(observation, dtype=np.float64).reshape(-1)
    if p.shape != (y.size, y.size):
        raise ValueError("projector shape does not match observation dimension")
    explained = p @ y
    residual = y - explained
    return explained, residual


@dataclass(frozen=True)
class AugmentedRepresentation:
    raw: np.ndarray
    reference: np.ndarray
    explained: np.ndarray
    residual: np.ndarray


def augment_representation(
    raw: np.ndarray, reference: np.ndarray, projector: np.ndarray
) -> AugmentedRepresentation:
    """Build the information-safe augmented representation."""

    y = np.asarray(raw, dtype=np.float64).reshape(-1)
    r = np.asarray(reference, dtype=np.float64).copy()
    explained, residual = decompose(projector, y)
    return AugmentedRepresentation(
        raw=y.copy(),
        reference=r,
        explained=explained,
        residual=residual,
    )


def adversarial_target_for_projector(projector: np.ndarray, *, atol: float = 1e-10) -> np.ndarray:
    """Return a unit target erased by a nonzero orthogonal projector.

    Raises ``ValueError`` for the zero projector because no nonzero vector can be
    erased by subtracting a zero projection.
    """

    p = np.asarray(projector, dtype=np.float64)
    if p.ndim != 2 or p.shape[0] != p.shape[1]:
        raise ValueError("projector must be square")
    eigenvalues, eigenvectors = np.linalg.eigh((p + p.T) / 2.0)
    index = int(np.argmax(eigenvalues))
    if float(eigenvalues[index]) <= atol:
        raise ValueError("projector has no nontrivial range")
    target = eigenvectors[:, index]
    norm = float(np.linalg.norm(target))
    return target / norm
