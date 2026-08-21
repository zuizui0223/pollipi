"""Portable deterministic visual worlds shared only as a benchmark contract.

The renderer is intentionally tiny and target-agnostic.  PolliPi and InsePi
carry byte-for-byte equivalent implementations so both front ends receive the
same pixels without importing one another.  A fixed SHA-256 fingerprint guards
cross-repository parity.
"""
from __future__ import annotations

import hashlib
from typing import Iterable

import numpy as np

SCENARIO_IDS: tuple[str, ...] = (
    "quiet_absence", "clean_visit", "wind_absence", "wind_visit",
    "shake_absence", "shake_visit", "shadow_absence", "shadow_visit",
    "occluded_visit", "blurred_visit", "clutter_visit", "unknown_visit",
)
PORTABLE_VISUAL_V2_FINGERPRINT = "f281fedd7ebf899dbc472b73b21afd25a30f18bb5481af71ec65b13f63a80ec8"


def render_pair(
    scenario_id: str,
    *,
    size: tuple[int, int] = (96, 128),
    seed: int = 20260821,
) -> tuple[np.ndarray, np.ndarray, bool]:
    if scenario_id not in SCENARIO_IDS:
        raise ValueError(f"unknown scenario_id: {scenario_id}")
    rng = np.random.default_rng(seed)
    height, width = size
    yy, xx = np.mgrid[:height, :width]
    base = (
        92
        + 18 * np.sin(xx * 0.11)
        + 11 * np.cos(yy * 0.17)
        + 6 * np.sin((xx + yy) * 0.07)
        + rng.normal(0, 2.0, size=(height, width))
    )
    frame = base.copy()
    true_visit = scenario_id.endswith("_visit") or scenario_id in {
        "occluded_visit", "blurred_visit", "clutter_visit", "clean_visit", "unknown_visit"
    }
    if true_visit:
        cy, cx = height // 2, width // 2
        amplitude, radius = 78.0, 5.5
        if scenario_id == "occluded_visit":
            amplitude = 28.0
        if scenario_id == "blurred_visit":
            amplitude, radius = 35.0, 10.0
        blob = amplitude * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * radius**2))
        frame += blob

    if scenario_id.startswith("wind_"):
        frame += 28 * (np.sin(xx * 0.22 + yy * 0.03) > 0)
    elif scenario_id.startswith("shake_"):
        frame = np.roll(np.roll(frame, 3, axis=0), 5, axis=1)
    elif scenario_id.startswith("shadow_"):
        center = width * 0.55
        shadow = np.exp(-((xx - center) ** 2) / (2 * (width * 0.22) ** 2))
        frame -= 42 * shadow
    elif scenario_id == "occluded_visit":
        frame[height // 2 - 7 : height // 2 + 8, width // 2 - 7 : width // 2 + 8] = (
            94 + rng.normal(0, 2, (15, 15))
        )
    elif scenario_id == "blurred_visit":
        frame = 0.75 * base + 0.25 * frame
    elif scenario_id == "clutter_visit":
        for cy, cx in ((20, 25), (72, 100), (25, 94), (70, 30)):
            frame += 55 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 7**2))
    elif scenario_id == "unknown_visit":
        frame += rng.normal(0, 12, size=(height, width))

    base_u8 = np.clip(np.rint(base), 0, 255).astype(np.uint8)
    frame_u8 = np.clip(np.rint(frame), 0, 255).astype(np.uint8)
    return base_u8, frame_u8, true_visit


def suite_fingerprint(ids: Iterable[str] = SCENARIO_IDS) -> str:
    digest = hashlib.sha256()
    for scenario_id in ids:
        background, frame, truth = render_pair(scenario_id)
        digest.update(scenario_id.encode("utf-8"))
        digest.update(background.tobytes())
        digest.update(frame.tobytes())
        digest.update(bytes([int(truth)]))
    return digest.hexdigest()
