"""Whole-frame overlapping spatial meshes.

The working baseline is a rectangular mesh plus a second rectangular mesh shifted
by approximately half a cell. A hexagonal layout is provided for comparison only
(Issue #14 prefers hex eventually) and must not replace the rectangular baseline
prematurely.

These functions operate on a boolean residual-activity mask and return per-cell
activity scores (fraction of changed pixels in the cell). They are pure and
numpy-only.
"""
from __future__ import annotations

from typing import Any

RECTANGULAR = "rectangular"
RECTANGULAR_OFFSET = "rectangular_offset_baseline"
HEXAGONAL = "hexagonal"


def rectangular_cells(mask, *, cell_size: int, offset_y: int = 0, offset_x: int = 0) -> list[dict[str, Any]]:
    """Aggregate ``mask`` into rectangular cells.

    Each returned cell carries its integer grid ``coord`` (row, col), pixel-space
    ``center``, and ``score`` (mean of the boolean mask inside the cell).
    """
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
            if y1 > max(0, y) and x1 > max(0, x):
                y0 = max(0, y)
                x0 = max(0, x)
                cells.append(
                    {
                        "coord": (row, col),
                        "center": ((x0 + x1) / 2.0, (y0 + y1) / 2.0),
                        "score": float(mask[y0:y1, x0:x1].mean()),
                    }
                )
            x += cell_size
            col += 1
        y += cell_size
        row += 1
    return cells


def hexagonal_cells(mask, *, cell_size: int) -> list[dict[str, Any]]:
    """Approximate hexagonal tessellation via odd-row half-cell horizontal shift.

    Provided for layout comparison only. Adjacency is not used downstream yet;
    the rectangular baseline remains the production layout.
    """
    height, width = mask.shape
    cells: list[dict[str, Any]] = []
    row = 0
    y = 0
    while y < height:
        x = (cell_size // 2) if (row % 2 == 1) else 0
        col = 0
        while x < width:
            y1 = min(height, y + cell_size)
            x1 = min(width, x + cell_size)
            if y1 > max(0, y) and x1 > max(0, x):
                x0 = max(0, x)
                cells.append(
                    {
                        "coord": (row, col),
                        "center": ((x0 + x1) / 2.0, (y + y1) / 2.0),
                        "score": float(mask[y:y1, x0:x1].mean()),
                    }
                )
            x += cell_size
            col += 1
        y += cell_size
        row += 1
    return cells


def active_coords(cells: list[dict[str, Any]], *, threshold: float) -> set[tuple[int, int]]:
    return {cell["coord"] for cell in cells if cell["score"] >= threshold}


def largest_connected_component(active: set[tuple[int, int]]) -> int:
    """4-neighbour connected-component size over active rectangular cells."""
    remaining = set(active)
    largest = 0
    while remaining:
        stack = [remaining.pop()]
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
