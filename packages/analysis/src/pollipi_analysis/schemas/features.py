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
    # Jaccard overlap of active-cell sets across consecutive frames. Logged as
    # explainable evidence only; NOT used by the V1 runtime decision.
    active_set_jaccard: float
    # --- global / common-mode evidence (used to reject noise) ---
    global_synchrony: float
    estimated_global_shift: float
    # --- bookkeeping ---
    cell_size: int
    mesh_layout: str = "rectangular_offset_baseline"

    # --- A/B cell-aggregation experiment (shadow-logged, NOT used by the active
    #     decision yet). Active-cell proportion under different per-cell reducers
    #     of the residual magnitude, after spatial common-mode subtraction.
    #     `max`/`q90`/`q95` retain a tiny compact (low-SNR) target that the mean
    #     can erase, at the cost of amplifying speckle noise — hence the A/B. ---
    active_proportion_mean: Optional[float] = None
    active_proportion_max: Optional[float] = None
    active_proportion_q90: Optional[float] = None
    active_proportion_q95: Optional[float] = None
    concentration_max: Optional[float] = None

    # --- trajectory features over the shadow track window (filled by the shadow
    #     runner from a centroid ring buffer; NOT used by the active decision). ---
    mean_step: Optional[float] = None
    reversal_rate: Optional[float] = None
    track_frames: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
