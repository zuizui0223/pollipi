"""Deterministic frame generators for calibrating mesh motion rules."""
from __future__ import annotations

from typing import Literal

Scenario = Literal["localized_trajectory", "broad_wind", "camera_shake", "oscillation", "shadow"]


def simulate_pair(scenario: Scenario, *, size: tuple[int, int] = (192, 256), seed: int = 7):
    """Return ``(background, frame)`` arrays for a named synthetic motion scenario."""
    import numpy as np

    rng = np.random.default_rng(seed)
    height, width = size
    background = np.full((height, width), 96, dtype=np.float32)
    background += np.linspace(-22, 22, width, dtype=np.float32)[None, :]
    background += np.linspace(-8, 8, height, dtype=np.float32)[:, None]
    background += rng.normal(0, 1.5, size=(height, width)).astype(np.float32)
    frame = background.copy()

    if scenario == "localized_trajectory":
        _draw_disc(frame, int(height * 0.48), int(width * 0.42), radius=7, value=170)
        _draw_disc(frame, int(height * 0.51), int(width * 0.48), radius=7, value=168)
    elif scenario == "broad_wind":
        stripes = (np.sin(np.linspace(0, 8, width))[None, :] > 0).astype(np.float32)
        frame += 36 * stripes
    elif scenario == "camera_shake":
        frame = np.roll(background, shift=6, axis=1)
    elif scenario == "oscillation":
        _draw_disc(frame, int(height * 0.5), int(width * 0.5), radius=18, value=132)
    elif scenario == "shadow":
        frame[:, int(width * 0.2): int(width * 0.85)] -= 28
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    return background, frame


def _draw_disc(frame, cy: int, cx: int, *, radius: int, value: float) -> None:
    import numpy as np

    yy, xx = np.ogrid[:frame.shape[0], :frame.shape[1]]
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
    frame[mask] = value
