"""Finite decision-risk witnesses for V3–TNOA information ordering."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Hashable, Iterable, Sequence, TypeVar

W = TypeVar("W")
O = TypeVar("O", bound=Hashable)
A = TypeVar("A")


def minimum_empirical_risk(
    worlds: Sequence[W],
    *,
    observation: Callable[[W], O],
    actions: Sequence[A],
    loss: Callable[[A, W], float],
    weights: Iterable[float] | None = None,
) -> float:
    """Return minimum weighted empirical risk over all rules based on ``observation``.

    For each realized observation value, the optimal action is selected separately.
    This exactly computes the best risk available from a finite observation
    partition without enumerating every complete decision rule.
    """

    if not worlds:
        raise ValueError("worlds must be non-empty")
    if not actions:
        raise ValueError("actions must be non-empty")

    if weights is None:
        weight_values = [1.0] * len(worlds)
    else:
        weight_values = [float(value) for value in weights]
        if len(weight_values) != len(worlds):
            raise ValueError("weights must match worlds")
        if any(value < 0.0 for value in weight_values):
            raise ValueError("weights must be non-negative")

    total_weight = sum(weight_values)
    if total_weight <= 0.0:
        raise ValueError("weights must have positive total")

    groups: dict[O, list[tuple[W, float]]] = defaultdict(list)
    for world, weight in zip(worlds, weight_values, strict=True):
        groups[observation(world)].append((world, weight))

    total_loss = 0.0
    for group in groups.values():
        candidate_losses = []
        for action in actions:
            candidate_losses.append(
                sum(weight * float(loss(action, world)) for world, weight in group)
            )
        total_loss += min(candidate_losses)
    return total_loss / total_weight


def decomposition_pair_is_reversible(
    explained: Sequence[float], residual: Sequence[float], raw: Sequence[float]
) -> bool:
    """Check exact algebraic reconstruction ``raw = explained + residual``."""

    e = tuple(float(value) for value in explained)
    z = tuple(float(value) for value in residual)
    y = tuple(float(value) for value in raw)
    if len(e) != len(z) or len(e) != len(y):
        raise ValueError("explained, residual and raw must have equal lengths")
    return all((a + b) == c for a, b, c in zip(e, z, y, strict=True))
