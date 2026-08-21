"""Held-out factorial visual world for methods-paper simulation.

Calibration contains clean and single-disturbance worlds. Test uses different
seeds/intensities and adds mixed disturbances plus a lens-obscuration OOD family.
This file has an equivalent sibling implementation in InsePi; a suite fingerprint
guards pixel parity without coupling decision logic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

import numpy as np

FACTORIAL_V4_FINGERPRINT = "10e38358499b79829876752986492c6a69b3ab15ec7b6756e6ae7ad75b314193"


@dataclass(frozen=True, slots=True)
class FactorialCondition:
    condition_id: str
    split: str
    seed: int
    true_visit: bool
    event_visibility: float
    wind: float = 0.0
    shake: float = 0.0
    shadow: float = 0.0
    occlusion: float = 0.0
    blur: float = 0.0
    clutter: float = 0.0
    lens: float = 0.0


def build_registry() -> tuple[FactorialCondition, ...]:
    rows: list[FactorialCondition] = []
    for split, seeds, intensities in (
        ("calibration", (11, 23), (0.45, 0.90)),
        ("test", (101, 131), (0.65, 1.15)),
    ):
        for seed in seeds:
            for true_visit in (False, True):
                suffix = int(true_visit)
                rows.append(FactorialCondition(
                    f"{split}-clean-{seed}-{suffix}", split, seed, true_visit, 1.0
                ))
                for name in ("wind", "shake", "shadow", "occlusion", "blur", "clutter"):
                    for intensity in intensities:
                        rows.append(FactorialCondition(
                            f"{split}-{name}-{intensity:.2f}-{seed}-{suffix}",
                            split,
                            seed,
                            true_visit,
                            1.0,
                            **{name: intensity},
                        ))
                if split == "test":
                    rows.extend((
                        FactorialCondition(
                            f"test-wind-shadow-{seed}-{suffix}", "test", seed, true_visit, 0.80,
                            wind=0.85, shadow=0.80,
                        ),
                        FactorialCondition(
                            f"test-shake-clutter-{seed}-{suffix}", "test", seed, true_visit, 0.80,
                            shake=0.90, clutter=0.90,
                        ),
                        FactorialCondition(
                            f"test-occlusion-blur-{seed}-{suffix}", "test", seed, true_visit, 0.65,
                            occlusion=0.80, blur=0.75,
                        ),
                        FactorialCondition(
                            f"test-lens-ood-{seed}-{suffix}", "test", seed, true_visit, 0.80,
                            lens=0.90,
                        ),
                    ))
    return tuple(rows)


def render_condition(
    condition: FactorialCondition,
    *,
    size: tuple[int, int] = (96, 128),
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(condition.seed)
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

    if condition.true_visit:
        cy, cx = height // 2, width // 2
        frame += (78 * condition.event_visibility) * np.exp(
            -((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 5.5**2)
        )
    if condition.wind:
        frame += 28 * condition.wind * (np.sin(xx * 0.22 + yy * 0.03) > 0)
    if condition.shadow:
        center = width * 0.55
        frame -= 42 * condition.shadow * np.exp(
            -((xx - center) ** 2) / (2 * (width * 0.22) ** 2)
        )
    if condition.clutter:
        for cy, cx in ((20, 25), (72, 100), (25, 94), (70, 30)):
            frame += 55 * condition.clutter * np.exp(
                -((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 7**2)
            )
    if condition.occlusion:
        ys = slice(height // 2 - 7, height // 2 + 8)
        xs = slice(width // 2 - 7, width // 2 + 8)
        patch = 94 + rng.normal(0, 2, (15, 15))
        frame[ys, xs] = (1 - condition.occlusion) * frame[ys, xs] + condition.occlusion * patch
    if condition.blur:
        for _ in range(max(1, round(3 * condition.blur))):
            smoothed = (
                frame
                + np.roll(frame, 1, 0)
                + np.roll(frame, -1, 0)
                + np.roll(frame, 1, 1)
                + np.roll(frame, -1, 1)
            ) / 5
            amount = min(1.0, condition.blur)
            frame = (1 - amount) * frame + amount * smoothed
    if condition.lens:
        cy, cx = int(height * 0.35), int(width * 0.35)
        mask = np.exp(
            -((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (min(height, width) * 0.14) ** 2)
        )
        frame = (1 - condition.lens * mask) * frame + condition.lens * mask * 145
    if condition.shake:
        dy = max(-6, min(6, round(3 * condition.shake)))
        dx = max(-8, min(8, round(5 * condition.shake)))
        frame = np.roll(np.roll(frame, dy, 0), dx, 1)

    return (
        np.clip(np.rint(base), 0, 255).astype(np.uint8),
        np.clip(np.rint(frame), 0, 255).astype(np.uint8),
    )


def suite_fingerprint() -> str:
    digest = hashlib.sha256()
    for condition in build_registry():
        background, frame = render_condition(condition)
        digest.update(json.dumps(asdict(condition), sort_keys=True, separators=(",", ":")).encode("utf-8"))
        digest.update(background.tobytes())
        digest.update(frame.tobytes())
    return digest.hexdigest()
