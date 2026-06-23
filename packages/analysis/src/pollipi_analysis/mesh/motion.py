"""Explainable overlapping-mesh motion analysis for scheduled timelapse frames."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

NO_ACTIVITY = "no_activity"
ENVIRONMENTAL_NOISE = "environmental_noise"
VISITATION_CANDIDATE = "visitation_candidate"


@dataclass(frozen=True)
class MeshConfig:
    cell_size: int = 48
    active_cell_threshold: float = 0.08
    pixel_difference: int = 30


def analyze_mesh_motion(
    frame,
    background,
    *,
    pixel_difference: int = 30,
    cell_size: int = 48,
    previous_active_cells: Optional[set[tuple[int, int]]] = None,
) -> dict[str, Any]:
    import numpy as np

    current = _as_gray(frame).astype(np.float32)
    baseline = _as_gray(background).astype(np.float32)
    if current.shape != baseline.shape:
        raise ValueError("frame and background must have the same luminance shape")

    changed = np.abs(current - baseline) >= pixel_difference
    primary = _mesh_cells(changed, cell_size=cell_size, offset_y=0, offset_x=0)
    offset = _mesh_cells(changed, cell_size=cell_size, offset_y=cell_size // 2, offset_x=cell_size // 2)

    active = {cell["coord"] for cell in primary if cell["score"] >= 0.08}
    active_prop = len(active) / max(1, len(primary))
    offset_active = {cell["coord"] for cell in offset if cell["score"] >= 0.08}
    offset_prop = len(offset_active) / max(1, len(offset))
    offset_agreement = 1.0 - min(1.0, abs(active_prop - offset_prop) * 4.0)

    largest_component = _largest_component_size(active)
    concentration = _concentration(primary)
    centroid = _centroid(primary)
    transition = _transition_score(active, previous_active_cells)
    global_synchrony = float(changed.mean())
    return_origin = _return_to_origin_score(active, previous_active_cells)

    if global_synchrony < 0.001 or active_prop < 0.015:
        classification = NO_ACTIVITY
        reason = "below_active_cell_threshold"
    elif global_synchrony >= 0.18 or active_prop >= 0.45 or largest_component >= max(4, int(len(primary) * 0.25)):
        classification = ENVIRONMENTAL_NOISE
        reason = "broad_common_mode_motion"
    elif return_origin >= 0.6 and transition < 0.15:
        classification = ENVIRONMENTAL_NOISE
        reason = "oscillation_or_return_to_origin"
    elif concentration >= 0.35 and active_prop <= 0.25 and offset_agreement >= 0.45:
        classification = VISITATION_CANDIDATE
        reason = "localized_overlapping_mesh_motion"
    else:
        classification = ENVIRONMENTAL_NOISE
        reason = "diffuse_or_low_confidence_motion"

    return {
        "mesh_decision": classification,
        "mesh_reason": reason,
        "mesh_layout": "rectangular_offset_baseline",
        "mesh_cell_size": cell_size,
        "mesh_active_cell_proportion": active_prop,
        "mesh_largest_component_cells": largest_component,
        "mesh_concentration": concentration,
        "mesh_offset_agreement": offset_agreement,
        "mesh_global_synchrony": global_synchrony,
        "mesh_transition_score": transition,
        "mesh_return_to_origin_score": return_origin,
        "mesh_centroid_x": centroid[0],
        "mesh_centroid_y": centroid[1],
        "mesh_active_cells": active,
    }


def compact_mesh_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    compact = dict(metrics)
    compact.pop("mesh_active_cells", None)
    return compact


def _as_gray(array):
    import numpy as np

    arr = np.asarray(array)
    if arr.ndim == 3:
        return arr[:, :, 0]
    return arr


def _mesh_cells(mask, *, cell_size: int, offset_y: int, offset_x: int) -> list[dict[str, Any]]:
    height, width = mask.shape
    cells: list[dict[str, Any]] = []
    y = offset_y
    row = 0
    while y < height:
        x = offset_x
        col = 0
        while x < width:
            y1 = min(height, y + cell_size)
            x1 = min(width, x + cell_size)
            if y1 > y and x1 > x:
                cells.append({
                    "coord": (row, col),
                    "center": ((x + x1) / 2.0, (y + y1) / 2.0),
                    "score": float(mask[y:y1, x:x1].mean()),
                })
            x += cell_size
            col += 1
        y += cell_size
        row += 1
    return cells


def _largest_component_size(active: set[tuple[int, int]]) -> int:
    remaining = set(active)
    largest = 0
    while remaining:
        start = remaining.pop()
        stack = [start]
        size = 1
        while stack:
            row, col = stack.pop()
            for neighbor in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
                    size += 1
        largest = max(largest, size)
    return largest


def _concentration(cells: list[dict[str, Any]]) -> float:
    total = sum(cell["score"] for cell in cells)
    if total <= 0:
        return 0.0
    return max(cell["score"] for cell in cells) / total


def _centroid(cells: list[dict[str, Any]]) -> tuple[Optional[float], Optional[float]]:
    total = sum(cell["score"] for cell in cells)
    if total <= 0:
        return None, None
    x = sum(cell["center"][0] * cell["score"] for cell in cells) / total
    y = sum(cell["center"][1] * cell["score"] for cell in cells) / total
    return float(x), float(y)


def _transition_score(active: set[tuple[int, int]], previous: Optional[set[tuple[int, int]]]) -> float:
    if not previous:
        return 0.0
    moved_neighbors = 0
    for row, col in active:
        if any((row + dy, col + dx) in previous for dy, dx in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))):
            moved_neighbors += 1
    return moved_neighbors / max(1, len(active))


def _return_to_origin_score(active: set[tuple[int, int]], previous: Optional[set[tuple[int, int]]]) -> float:
    if not previous or not active:
        return 0.0
    return len(active & previous) / max(1, len(active | previous))
