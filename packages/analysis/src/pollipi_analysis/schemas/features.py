"""Explainable mesh feature vector.

Every field is a plain float/int so the record can be logged to CSV, compared in
tests, and audited after the fact. No field implies a confirmed visit; they are
the raw, explainable evidence behind a :class:`MeshDecision`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class MeshFeatures:
    # --- per-cell residual activity (primary rectangular mesh) ---
    active_cell_proportion: float
    largest_component_cells: int
    concentration: float
    spatial_concentration: float
    # --- overlapping (half-cell offset) mesh agreement ---
    offset_active_cell_proportion: float
    offset_agreement: float
    # --- temporal evidence across the analysed pair / track ---
    persistence: float
    centroid_x: Optional[float]
    centroid_y: Optional[float]
    centroid_displacement: Optional[float]
    path_efficiency: Optional[float]
    direction_reversal: float
    # --- global / common-mode evidence (used to reject noise) ---
    global_synchrony: float
    estimated_global_shift: float
    # --- bookkeeping ---
    cell_size: int
    mesh_layout: str = "rectangular_offset_baseline"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
