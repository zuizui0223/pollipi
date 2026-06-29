"""R5 synthetic scenario sequences, ported verbatim from the six-round study.

Only the R5 *stimulus generation* is reused here (wind, local_sway, shadow,
camera_shake, and the target_* trajectories). The original study's 16-frame
aggregate features and its own classifier are NOT reused — the runtime bridge
feeds these raw frames through ``pollipi_analysis.pipeline.analyze`` instead, so
the search calibrates the actual Pi runtime. The R6 rolling temporal-median
background is intentionally absent: the Pi runtime has no such stage.

Frames are float in [0, 1] at the study's native 72x112; the bridge rescales
them to the Pi luminance scale before analysis.
"""
from __future__ import annotations

from typing import Any

import numpy as np

# Native study geometry (kept identical so the tuned scenario structure is reused).
SEED = 20260623
H, W = 72, 112
N_FRAMES = 16

# scenario -> truth family ("noise" or "target").
SCENARIOS: dict[str, str] = {
    "wind": "noise",
    "local_sway": "noise",
    "shadow": "noise",
    "camera_shake": "noise",
    "target_clean": "target",
    "target_edge": "target",
    "target_low_snr": "target",
    "target_wind": "target",
    "target_shadow": "target",
    "target_local_sway": "target",
    "target_wind_shadow": "target",
}


def base_scene(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    frame = 0.48 + 0.055 * np.sin(xx / 7.1) + 0.04 * np.cos(yy / 5.3)
    for _ in range(12):
        cx, cy = rng.uniform(0, W), rng.uniform(0, H)
        sx, sy = rng.uniform(3.5, 14), rng.uniform(3.5, 14)
        amp = rng.uniform(-0.09, 0.10)
        frame += amp * np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) / 2)
    return np.clip(frame, 0, 1)


def shift_image(image: np.ndarray, dx: float, dy: float) -> np.ndarray:
    ix, iy = int(round(dx)), int(round(dy))
    out = np.zeros_like(image)
    sy0, sy1 = max(0, -iy), min(H, H - iy)
    sx0, sx1 = max(0, -ix), min(W, W - ix)
    dy0, dy1 = max(0, iy), min(H, H + iy)
    dx0, dx1 = max(0, ix), min(W, W + ix)
    out[dy0:dy1, dx0:dx1] = image[sy0:sy1, sx0:sx1]
    return out


def add_target(image: np.ndarray, x: float, y: float, amp: float, radius: float) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W]
    blob = amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * radius ** 2))
    return np.clip(image + blob, 0, 1)


def add_shadow(image: np.ndarray, t: int, frames: int, strength: float = 0.22) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W]
    center = -14 + (W + 28) * t / max(frames - 1, 1)
    shadow = strength / (1 + np.exp(-(xx - center) / 5.0))
    return np.clip(image - shadow, 0, 1)


def local_sway(image: np.ndarray, t: int) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W]
    weight = np.exp(-((xx - W * 0.48) ** 2 + (yy - H * 0.54) ** 2) / (2 * 22 ** 2))
    movement = 3.0 * np.sin(2 * np.pi * t / 4.8)
    moved = shift_image(image, movement, 0.3 * movement)
    return np.clip((1 - weight) * image + weight * moved, 0, 1)


def generate_sequence(name: str, seed: int) -> np.ndarray:
    """Return an ``(N_FRAMES, H, W)`` float[0,1] sequence for scenario ``name``."""
    rng = np.random.default_rng(seed)
    scene = base_scene(seed)
    x0, y0 = rng.uniform(10, W - 26), rng.uniform(12, H - 18)
    theta = rng.uniform(-0.65, 0.65)
    speed = rng.uniform(0.8, 1.55)
    frames = []

    for t in range(N_FRAMES):
        frame = scene.copy()

        if name in {"wind", "target_wind", "target_wind_shadow"}:
            dx = 2.2 * np.sin(2 * np.pi * t / 5.8)
            frame = shift_image(frame, dx, 0.3 * dx)

        if name in {"local_sway", "target_local_sway"}:
            frame = local_sway(frame, t)

        if name in {"shadow", "target_shadow", "target_wind_shadow"}:
            frame = add_shadow(frame, t, N_FRAMES)

        if name == "camera_shake":
            frame = shift_image(frame, rng.normal(0, 1.8), rng.normal(0, 1.1))

        if name.startswith("target_"):
            if name == "target_edge":
                x = -2 + (W + 4) * t / max(N_FRAMES - 1, 1)
                y = H * 0.58 + 3 * np.sin(t / 2.5)
            else:
                x = x0 + speed * t * np.cos(theta) + 2 * np.sin(t / 3.2)
                y = y0 + speed * t * np.sin(theta) + 1.7 * np.cos(t / 4.4)
            amp = 0.20 if name == "target_low_snr" else 0.52
            radius = 1.25 if name == "target_low_snr" else 1.75
            frame = add_target(frame, x, y, amp, radius)

        noise_sigma = 0.020 if name == "target_low_snr" else 0.010
        frame += rng.normal(0, noise_sigma, frame.shape)
        frames.append(np.clip(frame, 0, 1))

    return np.asarray(frames)
