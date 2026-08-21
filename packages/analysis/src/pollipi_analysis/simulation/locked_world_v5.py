"""Commit-derived, shifted visual world for one-shot V5 validation.

The two repositories carry byte-equivalent copies of this renderer. Decision
logic remains repository-local; only conditions, pixels, truth, and provenance
are shared. Contract tests use synthetic commit IDs and therefore do not reveal
the eventual locked validation worlds.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass

import numpy as np

V4_WORLD_FINGERPRINT = "10e38358499b79829876752986492c6a69b3ab15ec7b6756e6ae7ad75b314193"
SEED_DOMAIN = "pollipi-insepi-v5-locked-validation"
CONTRACT_POLLIPI_COMMIT = "0" * 40
CONTRACT_INSEPI_COMMIT = "1" * 40
CONTRACT_FINGERPRINT = "f346d3ca68ebcfdd746032fe04c5f9f4adb30b083a8cc10917d618ef322687fd"

PREVALENCE_REGIMES = (
    ("rare", 0.20),
    ("balanced", 0.50),
    ("common", 0.80),
)
DISTURBANCE_FAMILIES = (
    "clean",
    "wind",
    "shake",
    "shadow",
    "occlusion",
    "smear",
    "clutter",
    "lens",
    "wind+shadow",
    "occlusion+smear",
    "shake+clutter",
    "lens+shadow",
)


@dataclass(frozen=True, slots=True)
class LockedConditionV5:
    condition_id: str
    prevalence_regime: str
    seed: int
    true_visit: bool
    disturbance_family: str
    event_contrast: float
    event_scale: float
    event_angle: float
    wind: float = 0.0
    shake_y: float = 0.0
    shake_x: float = 0.0
    shadow: float = 0.0
    occlusion: float = 0.0
    smear: float = 0.0
    clutter_count: int = 0
    lens_droplets: int = 0


def _validate_commit_sha(value: str, name: str) -> str:
    normalized = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40,64}", normalized):
        raise ValueError(f"{name} must be a full hexadecimal commit SHA")
    return normalized


def seed_material(pollipi_commit_sha: str, insepi_commit_sha: str) -> bytes:
    pollipi = _validate_commit_sha(pollipi_commit_sha, "pollipi_commit_sha")
    insepi = _validate_commit_sha(insepi_commit_sha, "insepi_commit_sha")
    return (
        f"{SEED_DOMAIN}\n{pollipi}\n{insepi}\n{V4_WORLD_FINGERPRINT}"
    ).encode("ascii")


def derive_seed_registry(
    pollipi_commit_sha: str,
    insepi_commit_sha: str,
    *,
    count: int,
) -> tuple[int, ...]:
    if count <= 0:
        raise ValueError("count must be positive")
    material = seed_material(pollipi_commit_sha, insepi_commit_sha)
    seeds: list[int] = []
    counter = 0
    while len(seeds) < count:
        block_material = material if counter == 0 else material + b"\n" + str(counter).encode("ascii")
        block = hashlib.sha256(block_material).digest()
        seeds.extend(int.from_bytes(block[offset:offset + 8], "big") for offset in range(0, 32, 8))
        counter += 1
    return tuple(seeds[:count])


def derive_competition_seed(pollipi_commit_sha: str, insepi_commit_sha: str) -> int:
    """Return a domain-separated seed for allocation competition replicates."""

    digest = hashlib.sha256(
        seed_material(pollipi_commit_sha, insepi_commit_sha) + b"\ncompetition"
    ).digest()
    return int.from_bytes(digest[:8], "big") % (2**31)


def build_registry(
    pollipi_commit_sha: str,
    insepi_commit_sha: str,
) -> tuple[LockedConditionV5, ...]:
    conditions_per_regime = len(DISTURBANCE_FAMILIES) * 5
    seeds = derive_seed_registry(
        pollipi_commit_sha,
        insepi_commit_sha,
        count=conditions_per_regime * len(PREVALENCE_REGIMES) + len(PREVALENCE_REGIMES),
    )
    rows: list[LockedConditionV5] = []
    seed_index = 0
    for regime_index, (regime, prevalence) in enumerate(PREVALENCE_REGIMES):
        schedule_seed = seeds[-len(PREVALENCE_REGIMES) + regime_index]
        schedule_rng = np.random.default_rng(schedule_seed)
        event_flags = np.zeros(conditions_per_regime, dtype=bool)
        event_flags[: round(prevalence * conditions_per_regime)] = True
        schedule_rng.shuffle(event_flags)
        position = 0
        for family in DISTURBANCE_FAMILIES:
            for replicate in range(5):
                condition_seed = seeds[seed_index]
                seed_index += 1
                rng = np.random.default_rng(condition_seed)
                strength = float(rng.uniform(0.35, 1.35))
                tokens = set(family.split("+"))
                true_visit = bool(event_flags[position])
                position += 1
                contrast = float(rng.uniform(38.0, 92.0))
                if rng.random() < 0.30:
                    contrast *= -1.0
                rows.append(LockedConditionV5(
                    condition_id=f"locked-{regime}-{family.replace('+', '-')}-{replicate}-{int(true_visit)}",
                    prevalence_regime=regime,
                    seed=condition_seed,
                    true_visit=true_visit,
                    disturbance_family=family,
                    event_contrast=contrast,
                    event_scale=float(rng.uniform(0.65, 1.55)),
                    event_angle=float(rng.uniform(-math.pi, math.pi)),
                    wind=strength if "wind" in tokens else 0.0,
                    shake_y=float(rng.uniform(-5.5, 5.5)) * strength if "shake" in tokens else 0.0,
                    shake_x=float(rng.uniform(-7.5, 7.5)) * strength if "shake" in tokens else 0.0,
                    shadow=strength if "shadow" in tokens else 0.0,
                    occlusion=strength if "occlusion" in tokens else 0.0,
                    smear=strength if "smear" in tokens else 0.0,
                    clutter_count=int(rng.integers(2, 8)) if "clutter" in tokens else 0,
                    lens_droplets=int(rng.integers(1, 5)) if "lens" in tokens else 0,
                ))
    return tuple(rows)


def _smooth(field: np.ndarray, iterations: int) -> np.ndarray:
    result = field.astype(np.float32)
    for _ in range(iterations):
        result = (
            4.0 * result
            + np.roll(result, 1, 0)
            + np.roll(result, -1, 0)
            + np.roll(result, 1, 1)
            + np.roll(result, -1, 1)
        ) / 8.0
    return result


def _standardize(field: np.ndarray) -> np.ndarray:
    scale = float(field.std())
    return (field - float(field.mean())) / scale if scale > 1e-9 else np.zeros_like(field)


def _superellipse(
    yy: np.ndarray,
    xx: np.ndarray,
    *,
    cy: float,
    cx: float,
    radius_y: float,
    radius_x: float,
    angle: float,
    power: float = 4.0,
) -> np.ndarray:
    dy, dx = yy - cy, xx - cx
    cosine, sine = math.cos(angle), math.sin(angle)
    rotated_x = cosine * dx + sine * dy
    rotated_y = -sine * dx + cosine * dy
    distance = (np.abs(rotated_x / radius_x) ** power) + (np.abs(rotated_y / radius_y) ** power)
    return np.exp(-distance)


def render_condition(
    condition: LockedConditionV5,
    *,
    size: tuple[int, int] = (96, 128),
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(condition.seed)
    height, width = size
    yy, xx = np.mgrid[:height, :width]
    coarse = _standardize(_smooth(rng.normal(size=size), 14))
    medium = _standardize(_smooth(rng.normal(size=size), 4))
    fine = _standardize(rng.normal(size=size))
    base = 104.0 + 20.0 * coarse + 9.0 * medium + 3.0 * fine
    frame = base.copy()

    if condition.true_visit:
        cy = height * float(rng.uniform(0.38, 0.62))
        cx = width * float(rng.uniform(0.38, 0.62))
        direction_y, direction_x = math.sin(condition.event_angle), math.cos(condition.event_angle)
        event = np.zeros(size, dtype=np.float32)
        for step in (-1, 0, 1):
            event = np.maximum(event, _superellipse(
                yy,
                xx,
                cy=cy + step * direction_y * 3.5 * condition.event_scale,
                cx=cx + step * direction_x * 3.5 * condition.event_scale,
                radius_y=3.0 * condition.event_scale,
                radius_x=6.5 * condition.event_scale,
                angle=condition.event_angle,
            ))
        frame += condition.event_contrast * event

    if condition.wind:
        wind_field = _standardize(_smooth(rng.normal(size=size), 6))
        coherent_mask = _smooth((rng.random(size) > 0.56).astype(np.float32), 3)
        frame += 17.0 * condition.wind * wind_field * (0.35 + coherent_mask)

    if condition.shadow:
        angle = float(rng.uniform(-0.9, 0.9))
        center = float(rng.uniform(-0.25, 0.25)) * width
        projected = math.cos(angle) * (xx - width / 2) + math.sin(angle) * (yy - height / 2)
        width_scale = float(rng.uniform(9.0, 25.0))
        band = np.exp(-((projected - center) / width_scale) ** 4)
        heterogeneity = np.clip(1.0 + 0.25 * _standardize(_smooth(rng.normal(size=size), 5)), 0.35, 1.65)
        frame -= 34.0 * condition.shadow * band * heterogeneity

    if condition.clutter_count:
        for _ in range(condition.clutter_count):
            mask = _superellipse(
                yy,
                xx,
                cy=float(rng.uniform(8, height - 8)),
                cx=float(rng.uniform(8, width - 8)),
                radius_y=float(rng.uniform(3.0, 10.0)),
                radius_x=float(rng.uniform(3.0, 12.0)),
                angle=float(rng.uniform(-math.pi, math.pi)),
                power=float(rng.choice((2.0, 4.0, 6.0))),
            )
            frame += float(rng.uniform(-58.0, 64.0)) * mask

    if condition.occlusion:
        cy = height * float(rng.choice((0.34, 0.43, 0.58, 0.66)))
        cx = width * float(rng.choice((0.32, 0.44, 0.57, 0.69)))
        mask = _superellipse(
            yy,
            xx,
            cy=cy,
            cx=cx,
            radius_y=float(rng.uniform(7.0, 15.0)),
            radius_x=float(rng.uniform(9.0, 19.0)),
            angle=float(rng.uniform(-math.pi, math.pi)),
            power=6.0,
        )
        alpha = np.clip(condition.occlusion * mask, 0.0, 0.96)
        replacement = 104.0 + 3.0 * _standardize(_smooth(rng.normal(size=size), 3))
        frame = (1.0 - alpha) * frame + alpha * replacement

    if condition.smear:
        angle = float(rng.uniform(-math.pi, math.pi))
        steps = max(2, round(3 + 4 * min(condition.smear, 1.5)))
        shifted = []
        for step in range(-steps, steps + 1):
            dy = round(step * math.sin(angle))
            dx = round(step * math.cos(angle))
            shifted.append(np.roll(np.roll(frame, dy, 0), dx, 1))
        amount = min(0.92, 0.38 + 0.38 * condition.smear)
        frame = (1.0 - amount) * frame + amount * np.mean(shifted, axis=0)

    if condition.lens_droplets:
        for _ in range(condition.lens_droplets):
            cy = float(rng.uniform(0.12, 0.88) * height)
            cx = float(rng.uniform(0.12, 0.88) * width)
            radius = float(rng.uniform(7.0, 18.0))
            mask = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / radius**2) ** 2)
            refracted = np.roll(np.roll(frame, int(rng.integers(-3, 4)), 0), int(rng.integers(-4, 5)), 1)
            alpha = 0.72 * mask
            frame = (1.0 - alpha) * frame + alpha * (0.72 * refracted + 0.28 * 156.0)

    if condition.shake_y or condition.shake_x:
        dy0, dx0 = math.floor(condition.shake_y), math.floor(condition.shake_x)
        dy1, dx1 = math.ceil(condition.shake_y), math.ceil(condition.shake_x)
        shifted0 = np.roll(np.roll(frame, dy0, 0), dx0, 1)
        shifted1 = np.roll(np.roll(frame, dy1, 0), dx1, 1)
        blend = abs(condition.shake_x - dx0 + condition.shake_y - dy0) / 2.0
        frame = (1.0 - blend) * shifted0 + blend * shifted1

    return (
        np.clip(np.rint(base), 0, 255).astype(np.uint8),
        np.clip(np.rint(frame), 0, 255).astype(np.uint8),
    )


def suite_fingerprint(pollipi_commit_sha: str, insepi_commit_sha: str) -> str:
    digest = hashlib.sha256()
    for condition in build_registry(pollipi_commit_sha, insepi_commit_sha):
        background, frame = render_condition(condition)
        digest.update(json.dumps(asdict(condition), sort_keys=True, separators=(",", ":")).encode("utf-8"))
        digest.update(background.tobytes())
        digest.update(frame.tobytes())
    return digest.hexdigest()
