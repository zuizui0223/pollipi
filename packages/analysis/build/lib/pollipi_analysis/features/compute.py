"""Compute the explainable :class:`MeshFeatures` vector from two frames.

Pure numpy. Given a scheduled frame and its reference background, this runs the
preprocessing steps and the overlapping-mesh aggregation, then derives the
feature set the rule-based classifier and the simulator both consume.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional

from pollipi_analysis.features.preprocess import (
    apply_shift,
    estimate_global_shift,
    normalize_brightness,
    residual_image,
    to_gray,
)
from pollipi_analysis.mesh.grid import (
    active_coords,
    largest_connected_component,
    rectangular_cells,
)
from pollipi_analysis.schemas.features import MeshFeatures


@dataclass(frozen=True)
class FeatureConfig:
    cell_size: int = 32
    pixel_difference: int = 25
    active_cell_threshold: float = 0.08
    register: bool = True
    normalize_brightness: bool = True
    max_shift: int = 4


def compute_features(
    frame,
    background,
    *,
    config: Optional[FeatureConfig] = None,
    previous_active_cells: Optional[set[tuple[int, int]]] = None,
    previous_centroid: Optional[tuple[float, float]] = None,
) -> tuple[MeshFeatures, set[tuple[int, int]]]:
    """Return ``(features, active_cells)`` for one analysed frame pair."""
    import numpy as np

    cfg = config or FeatureConfig()

    cur = to_gray(frame)
    base = to_gray(background)
    if cur.shape != base.shape:
        raise ValueError("frame and background must share the same luminance shape")

    # 1. optional small global translation registration
    if cfg.register:
        dy, dx, shift_mag = estimate_global_shift(cur, base, max_shift=cfg.max_shift)
        if shift_mag > 0:
            cur = apply_shift(cur, dy, dx)
    else:
        shift_mag = 0.0

    # Compute an un-normalised residual first to capture broad global changes
    # (e.g. an exposure/illumination jump) that normalization would erase.
    raw_residual = residual_image(cur, base)
    raw_changed = raw_residual >= cfg.pixel_difference
    global_synchrony = float(raw_changed.mean())

    # 2. optional global brightness normalization (keeps local contrasts but
    # avoids treating gentle illumination drift as local motion). This runs after
    # computing the raw residual used for global-change detection.
    if cfg.normalize_brightness:
        cur = normalize_brightness(cur, base)

    # 3. residual motion image (after optional normalization)
    residual = residual_image(cur, base)
    changed = residual >= cfg.pixel_difference

    # 4. overlapping mesh aggregation (rectangular baseline + half-cell offset)
    half = cfg.cell_size // 2
    primary = rectangular_cells(changed, cell_size=cfg.cell_size, offset_y=0, offset_x=0)
    offset = rectangular_cells(changed, cell_size=cfg.cell_size, offset_y=half, offset_x=half)

    active = active_coords(primary, threshold=cfg.active_cell_threshold)
    offset_active = active_coords(offset, threshold=cfg.active_cell_threshold)
    active_prop = len(active) / max(1, len(primary))
    offset_prop = len(offset_active) / max(1, len(offset))
    offset_agreement = 1.0 - min(1.0, abs(active_prop - offset_prop) * 4.0)

    largest = largest_connected_component(active)
    concentration = _concentration(primary)
    spatial_concentration = _spatial_concentration(primary, active)
    centroid = _centroid(primary)
    persistence = _persistence(active, previous_active_cells)
    direction_reversal = _return_to_origin(active, previous_active_cells)
    centroid_displacement = _displacement(centroid, previous_centroid)

    features = MeshFeatures(
        active_cell_proportion=active_prop,
        largest_component_cells=largest,
        concentration=concentration,
        spatial_concentration=spatial_concentration,
        offset_active_cell_proportion=offset_prop,
        offset_agreement=offset_agreement,
        persistence=persistence,
        centroid_x=centroid[0],
        centroid_y=centroid[1],
        centroid_displacement=centroid_displacement,
        path_efficiency=None,  # filled by the track runner over a window
        direction_reversal=direction_reversal,
        global_synchrony=global_synchrony,
        estimated_global_shift=float(shift_mag),
        cell_size=cfg.cell_size,
    )
    return features, active


def _concentration(cells: list[dict[str, Any]]) -> float:
    total = sum(cell["score"] for cell in cells)
    if total <= 0:
        return 0.0
    return max(cell["score"] for cell in cells) / total


def _spatial_concentration(cells: list[dict[str, Any]], active: set[tuple[int, int]]) -> float:
    """Share of active-cell mass within ~1.5 grid steps of the activity centroid.

    1.0 means all activity is one compact blob; values near 0 mean activity is
    scattered across the whole frame (typical of broad wind/shadow).
    """
    if not active:
        return 0.0
    scored = {cell["coord"]: cell["score"] for cell in cells if cell["coord"] in active}
    total = sum(scored.values())
    if total <= 0:
        return 0.0
    cy = sum(r * s for (r, c), s in scored.items()) / total
    cx = sum(c * s for (r, c), s in scored.items()) / total
    near = sum(
        s
        for (r, c), s in scored.items()
        if math.hypot(r - cy, c - cx) <= 1.5
    )
    return near / total


def _centroid(cells: list[dict[str, Any]]) -> tuple[Optional[float], Optional[float]]:
    total = sum(cell["score"] for cell in cells)
    if total <= 0:
        return None, None
    x = sum(cell["center"][0] * cell["score"] for cell in cells) / total
    y = sum(cell["center"][1] * cell["score"] for cell in cells) / total
    return float(x), float(y)


def _persistence(active: set[tuple[int, int]], previous: Optional[set[tuple[int, int]]]) -> float:
    """Fraction of active cells that were active or adjacent in the previous frame."""
    if not previous or not active:
        return 0.0
    cont = 0
    for row, col in active:
        if any(
            (row + dy, col + dx) in previous
            for dy, dx in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))
        ):
            cont += 1
    return cont / max(1, len(active))


def _return_to_origin(active: set[tuple[int, int]], previous: Optional[set[tuple[int, int]]]) -> float:
    if not previous or not active:
        return 0.0
    return len(active & previous) / max(1, len(active | previous))


def _displacement(
    centroid: tuple[Optional[float], Optional[float]],
    previous: Optional[tuple[float, float]],
) -> Optional[float]:
    if previous is None or centroid[0] is None or centroid[1] is None:
        return None
    return float(math.hypot(centroid[0] - previous[0], centroid[1] - previous[1]))
