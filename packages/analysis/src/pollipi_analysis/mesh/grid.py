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


CELL_REDUCERS = ("mean", "max", "q90", "q95")


def aggregate_residual_grid(residual, *, cell_size: int, reducer: str = "mean", offset: bool = False):
    """Reduce a residual-magnitude image into a (rows, cols) per-cell grid.

    ``reducer`` is one of :data:`CELL_REDUCERS`. ``max``/``q90``/``q95`` keep a
    small compact (low-SNR) target that a cell mean would average away; ``mean``
    is the conservative, noise-robust baseline. Used for the shadow-only A/B
    aggregation comparison — it does not change the active decision.
    """
    import numpy as np

    arr = np.asarray(residual, dtype=np.float32)
    if offset:
        arr = np.roll(arr, (cell_size // 2, cell_size // 2), axis=(0, 1))
    height, width = arr.shape
    rows = max(1, height // cell_size)
    cols = max(1, width // cell_size)
    cropped = arr[: rows * cell_size, : cols * cell_size]
    blocks = cropped.reshape(rows, cell_size, cols, cell_size).transpose(0, 2, 1, 3)
    flat = blocks.reshape(rows, cols, cell_size * cell_size)
    if reducer == "mean":
        return flat.mean(axis=2)
    if reducer == "max":
        return flat.max(axis=2)
    if reducer == "q90":
        return np.quantile(flat, 0.90, axis=2)
    if reducer == "q95":
        return np.quantile(flat, 0.95, axis=2)
    raise ValueError(f"unknown reducer: {reducer!r}")


def grid_largest_component(mask) -> int:
    """4-neighbour largest connected component over a boolean (rows, cols) grid."""
    import numpy as np

    m = np.asarray(mask, dtype=bool)
    coords = {(int(r), int(c)) for r, c in zip(*np.nonzero(m))}
    return largest_connected_component(coords)


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
