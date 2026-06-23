"""Result of a single explainable three-state mesh decision."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pollipi_analysis.schemas.features import MeshFeatures
from pollipi_analysis.schemas.states import DecisionState


@dataclass(frozen=True)
class MeshDecision:
    """A rule-based, explainable classification of one analysed frame pair.

    ``state`` is one of the canonical decision states. ``reason`` is a short,
    stable token naming the rule branch that fired, so every decision is
    auditable. ``features`` carries the evidence that produced the state.
    """

    state: DecisionState
    reason: str
    features: MeshFeatures
    # Active cells are kept out of the flat log row but available for the next
    # frame's persistence/displacement computation.
    active_cells: frozenset[tuple[int, int]] = field(default_factory=frozenset)

    def flat(self) -> dict[str, Any]:
        """Flat, log-friendly dict (state + reason + features), no cell set."""
        row: dict[str, Any] = {"decision_state": self.state, "reason": self.reason}
        row.update(self.features.to_dict())
        return row
