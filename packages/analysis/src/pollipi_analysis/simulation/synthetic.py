"""Deterministic synthetic frame generators for calibrating mesh rules.

All generators take a fixed ``seed`` and are fully reproducible. They cover the
calibration cases required for shadow-mode preparation:

- clean localised target trajectories (incl. boundary crossing)
- broad wind, global shadow, moving shadow, camera shake (pure environment)
- local sway / oscillation
- mixed target + wind, target + shadow, target + local sway
- low-SNR targets

These are intentionally simplified; they are for rule calibration and regression
testing only and are NOT a claim of field-ready accuracy.
"""
from __future__ import annotations

from typing import Any

Scenario = str

# Single-pair scenarios kept backward compatible with earlier tests.
_PAIR_SCENARIOS = (
    "localized_trajectory",
    "broad_wind",
    "camera_shake",
    "oscillation",
    "shadow",
)


def _base_background(rng, size: tuple[int, int]):
    import numpy as np

    height, width = size
    background = np.full((height, width), 96, dtype=np.float32)
    background += np.linspace(-22, 22, width, dtype=np.float32)[None, :]
    background += np.linspace(-8, 8, height, dtype=np.float32)[:, None]
    background += rng.normal(0, 1.5, size=(height, width)).astype(np.float32)
    return background


def simulate_pair(scenario: Scenario, *, size: tuple[int, int] = (192, 256), seed: int = 7):
    """Return ``(background, frame)`` for a single-step scenario."""
    import numpy as np

    rng = np.random.default_rng(seed)
    height, width = size
    background = _base_background(rng, size)
    frame = background.copy()

    if scenario == "localized_trajectory":
        _draw_disc(frame, int(height * 0.48), int(width * 0.42), radius=7, value=170)
        _draw_disc(frame, int(height * 0.51), int(width * 0.48), radius=7, value=168)
    elif scenario == "boundary_crossing":
        # A compact target straddling a cell border.
        _draw_disc(frame, int(height * 0.45), int(width * 0.50), radius=8, value=175)
    elif scenario == "broad_wind":
        stripes = (np.sin(np.linspace(0, 8, width))[None, :] > 0).astype(np.float32)
        frame += 36 * stripes
    elif scenario == "camera_shake":
        frame = np.roll(background, shift=6, axis=1)
    elif scenario == "oscillation":
        _draw_disc(frame, int(height * 0.5), int(width * 0.5), radius=18, value=132)
    elif scenario == "shadow":
        frame[:, int(width * 0.2): int(width * 0.85)] -= 28
    elif scenario == "moving_shadow":
        frame[:, int(width * 0.3): int(width * 0.95)] -= 30
    elif scenario == "low_snr_target":
        _draw_disc(frame, int(height * 0.5), int(width * 0.45), radius=6, value=118)
        frame += rng.normal(0, 6.0, size=(height, width)).astype(np.float32)
    elif scenario == "target_plus_wind":
        stripes = (np.sin(np.linspace(0, 8, width))[None, :] > 0).astype(np.float32)
        frame += 30 * stripes
        _draw_disc(frame, int(height * 0.5), int(width * 0.45), radius=7, value=172)
    elif scenario == "target_plus_shadow":
        frame[:, int(width * 0.2): int(width * 0.85)] -= 26
        _draw_disc(frame, int(height * 0.5), int(width * 0.45), radius=7, value=174)
    elif scenario == "target_plus_sway":
        _draw_disc(frame, int(height * 0.30), int(width * 0.70), radius=9, value=128)
        _draw_disc(frame, int(height * 0.5), int(width * 0.45), radius=7, value=172)
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    return background, frame


def simulate_sequence(
    scenario: Scenario,
    *,
    size: tuple[int, int] = (192, 256),
    n_frames: int = 6,
    seed: int = 7,
) -> list[Any]:
    """Return a list of ``n_frames`` frames for a temporal scenario.

    Frame 0 is the clean background; consecutive frames feed the shadow runner,
    which compares each frame to its predecessor.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    height, width = size
    background = _base_background(rng, size)
    frames = [background.copy()]

    for i in range(1, n_frames):
        frame = background.copy()
        t = i / max(1, n_frames - 1)
        if scenario == "target_traverse":
            cx = int(width * (0.2 + 0.6 * t))
            cy = int(height * (0.4 + 0.1 * t))
            _draw_disc(frame, cy, cx, radius=7, value=172)
        elif scenario == "local_sway":
            # A compact, target-like object swaying back and forth around a fixed
            # point. Each pair looks localized/strong, but the centroid oscillates
            # so the track-level path efficiency stays low -> oscillation/noise.
            phase = float(np.sin(t * np.pi * 3))
            cx = int(width * 0.5 + phase * 18)
            _draw_disc(frame, int(height * 0.5), cx, radius=8, value=172)
        elif scenario == "moving_shadow":
            edge = int(width * (0.2 + 0.6 * t))
            frame[:, max(0, edge - int(width * 0.4)): edge] -= 28
        elif scenario == "broad_wind":
            stripes = (np.sin(np.linspace(0, 8, width) + t * 3)[None, :] > 0).astype(np.float32)
            frame += 34 * stripes
        elif scenario == "quiet":
            frame += rng.normal(0, 1.0, size=(height, width)).astype(np.float32)
        else:
            raise ValueError(f"unknown sequence scenario: {scenario}")
        frames.append(frame)
    return frames


def _draw_disc(frame, cy: int, cx: int, *, radius: int, value: float) -> None:
    import numpy as np

    yy, xx = np.ogrid[: frame.shape[0], : frame.shape[1]]
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
    frame[mask] = value
