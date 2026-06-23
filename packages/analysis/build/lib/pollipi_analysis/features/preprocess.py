"""Frame preprocessing steps: registration, brightness normalisation, residual.

These are the first stages of the analysis pipeline. Each step is optional and
side-effect free. We deliberately do NOT apply temporal-median background
subtraction here: synthetic tests showed it can erase small, weak targets along
with background noise, so median subtraction is not assumed to be beneficial and
is left out of the default path.
"""
from __future__ import annotations

from typing import Any


def to_gray(array) -> Any:
    import numpy as np

    arr = np.asarray(array)
    if arr.ndim == 3:
        return arr[:, :, 0].astype(np.float32)
    return arr.astype(np.float32)


def estimate_global_shift(frame, background, *, max_shift: int = 4) -> tuple[int, int, float]:
    """Estimate a small integer (dy, dx) translation of ``frame`` vs ``background``.

    Returns ``(dy, dx, magnitude)`` of the shift that minimises mean absolute
    difference over the overlapping region. A large magnitude is evidence of
    camera shake / drift rather than a localised visitor.
    """
    import numpy as np

    cur = to_gray(frame)
    base = to_gray(background)
    best = (0, 0)
    best_cost = float("inf")
    for dy in range(-max_shift, max_shift + 1):
        for dx in range(-max_shift, max_shift + 1):
            shifted = np.roll(np.roll(cur, dy, axis=0), dx, axis=1)
            # Ignore the wrapped border so np.roll wrap-around does not bias cost.
            ys = slice(abs(dy), cur.shape[0] - abs(dy)) if dy else slice(None)
            xs = slice(abs(dx), cur.shape[1] - abs(dx)) if dx else slice(None)
            cost = float(np.abs(shifted[ys, xs] - base[ys, xs]).mean())
            if cost < best_cost - 1e-6:
                best_cost = cost
                best = (dy, dx)
    dy, dx = best
    return dy, dx, float((dy * dy + dx * dx) ** 0.5)


def apply_shift(frame, dy: int, dx: int) -> Any:
    import numpy as np

    cur = to_gray(frame)
    return np.roll(np.roll(cur, -dy, axis=0), -dx, axis=1)


def normalize_brightness(frame, background) -> Any:
    """Remove a global brightness offset (e.g. a passing cloud / global shadow).

    Subtracts the median frame-minus-background offset so a uniform illumination
    change does not register as motion. Localised changes survive because the
    median is dominated by the unchanged majority of pixels.
    """
    import numpy as np

    cur = to_gray(frame)
    base = to_gray(background)
    offset = float(np.median(cur - base))
    return cur - offset


def residual_image(frame, background) -> Any:
    import numpy as np

    return np.abs(to_gray(frame) - to_gray(background))
