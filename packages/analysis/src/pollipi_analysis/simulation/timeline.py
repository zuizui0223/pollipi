"""Power-oriented timeline simulation (Phase 2 objective).

The earlier objective scored a policy by per-scenario detection accuracy. The
device's real goal is different: spend as little power as possible while still
entering the HIGH rate during genuine insect activity and *not* entering it for
wind / shadow / flower-sway. To score that, we have to simulate the actual
capture timeline, not classify isolated scenarios.

This module:

1. builds a long, labelled timeline at a fine base cadence — segments of quiet,
   broad wind, moving shadow, local sway, and directed insect traverses, with a
   per-tick ground-truth "insect present" flag; and
2. walks the timeline with the shared :class:`~pollipi_analysis.track.Tracker`
   and the :class:`~pollipi_analysis.policy.two_stage.TwoStageController`,
   capturing only when the controller schedules a capture, and reports power /
   coverage / false-HIGH metrics plus a single power-aware cost.

Everything uses the shared feature/decision/control code, so a policy's
simulated behaviour matches what the Pi would do on the same frames.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from pollipi_analysis.pipeline import PipelineConfig
from pollipi_analysis.policy.two_stage import HIGH, TwoStageConfig, TwoStageController
from pollipi_analysis.track import Tracker

TimelineKind = str
NOISE_KINDS = ("quiet", "broad_wind", "moving_shadow", "local_sway")
INSECT_KIND = "insect"


@dataclass(frozen=True)
class TimelineSegment:
    kind: TimelineKind
    ticks: int


def _draw_disc(frame, cy: int, cx: int, *, radius: int, value: float) -> None:
    import numpy as np

    yy, xx = np.ogrid[: frame.shape[0], : frame.shape[1]]
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2
    frame[mask] = value


def generate_timeline(
    segments: Sequence[TimelineSegment],
    *,
    size: tuple[int, int] = (192, 256),
    seed: int = 7,
):
    """Return ``(frames, truth)`` where ``truth[i]`` is True iff an insect is present.

    Frames are produced at a single fine base cadence (one frame per tick) from a
    shared background plus a per-kind perturbation whose phase advances with the
    global tick, so frame-to-frame residuals are realistic across segment joins.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    height, width = size
    background = np.full((height, width), 96, dtype=np.float32)
    background += np.linspace(-22, 22, width, dtype=np.float32)[None, :]
    background += np.linspace(-8, 8, height, dtype=np.float32)[:, None]

    frames = []
    truth: list[bool] = []
    tick = 0
    for segment in segments:
        for k in range(segment.ticks):
            frame = background + rng.normal(0, 1.0, size=(height, width)).astype(np.float32)
            is_insect = False
            if segment.kind == "quiet":
                pass
            elif segment.kind == "broad_wind":
                stripes = (np.sin(np.linspace(0, 8, width) + tick * 0.6)[None, :] > 0).astype(np.float32)
                frame += 34 * stripes
            elif segment.kind == "moving_shadow":
                t = k / max(1, segment.ticks - 1)
                edge = int(width * (0.2 + 0.6 * t))
                frame[:, max(0, edge - int(width * 0.4)) : edge] -= 28
            elif segment.kind == "local_sway":
                # Compact blob oscillating about a fixed point: each pair looks
                # localized, but the centroid reverses -> low path efficiency.
                phase = float(np.sin(k * np.pi * 0.6))
                cx = int(width * 0.5 + phase * 18)
                _draw_disc(frame, int(height * 0.5), cx, radius=8, value=172)
            elif segment.kind == INSECT_KIND:
                # A compact target traversing directedly across the window.
                t = k / max(1, segment.ticks - 1)
                cx = int(width * (0.2 + 0.6 * t))
                cy = int(height * (0.4 + 0.1 * t))
                _draw_disc(frame, cy, cx, radius=7, value=172)
                is_insect = True
            else:
                raise ValueError(f"unknown timeline kind: {segment.kind!r}")
            frames.append(frame)
            truth.append(is_insect)
            tick += 1
    return frames, truth


@dataclass(frozen=True)
class PowerMetrics:
    n_ticks: int
    base_rate_sec: float
    duration_sec: float
    captures: int
    captures_per_hour: float
    insect_ticks: int
    insect_ticks_in_high: int
    coverage: float            # fraction of insect ticks spent in HIGH (responsiveness)
    high_ticks: int
    false_high_ticks: int      # HIGH ticks with no insect present (wasted power)
    false_high_rate: float     # false_high_ticks / non-insect ticks
    missed_insect_ticks: int   # insect ticks the controller spent in LOW


@dataclass(frozen=True)
class PowerObjectiveWeights:
    """Power-aware cost weights.

    A false-HIGH tick burns power for nothing (wind/shadow): penalised most.
    Missing insect time loses the evidence the device exists to gather. Energy is
    the steady baseline draw. Minimising the weighted sum favours a policy that is
    quiet by default and only goes HIGH when it pays off.
    """

    energy_weight: float = 1.0          # per capture-per-hour
    false_high_weight: float = 12.0     # per unit false-HIGH rate
    miss_weight: float = 4.0            # per unit (1 - coverage)


def simulate_power(
    frames: Sequence,
    truth: Sequence[bool],
    *,
    base_rate_sec: float,
    controller_config: TwoStageConfig,
    pipeline_config: Optional[PipelineConfig] = None,
) -> PowerMetrics:
    """Walk the timeline, capturing only when the controller schedules a capture.

    ``base_rate_sec`` is the timeline's tick spacing and should equal the HIGH
    rate (the finest sampling the policy can reach). LOW skips ticks. Each capture
    is analysed against the previously captured frame via the shared Tracker, and
    the resulting decision drives the two-stage controller. The mode in effect
    between captures is attributed to every tick for coverage / false-HIGH.
    """
    n = len(frames)
    if n == 0:
        raise ValueError("empty timeline")

    tracker = Tracker(config=pipeline_config or PipelineConfig())
    controller = TwoStageController(config=controller_config)

    base = float(base_rate_sec)
    mode_per_tick: list[str] = [controller.mode] * n
    captures = 0
    last_captured_index: Optional[int] = None
    next_capture = 0  # tick index of the next scheduled capture

    i = 0
    while i < n:
        if i < next_capture:
            mode_per_tick[i] = controller.mode
            i += 1
            continue

        # Capture this tick.
        captures += 1
        if last_captured_index is None:
            # First (reference) capture: no decision, stay LOW, next at base step.
            step_ticks = 1
            mode_per_tick[i] = controller.mode
        else:
            decision = tracker.observe(frames[i], frames[last_captured_index])
            step = controller.step(decision.state, now_sec=i * base)
            mode_per_tick[i] = step.mode
            step_ticks = max(1, int(round(step.interval_sec / base)))
        last_captured_index = i
        next_capture = i + step_ticks
        i += 1

    insect_ticks = sum(1 for t in truth if t)
    non_insect = n - insect_ticks
    high_ticks = sum(1 for m in mode_per_tick if m == HIGH)
    insect_in_high = sum(1 for idx in range(n) if truth[idx] and mode_per_tick[idx] == HIGH)
    false_high = sum(1 for idx in range(n) if not truth[idx] and mode_per_tick[idx] == HIGH)
    duration = n * base

    return PowerMetrics(
        n_ticks=n,
        base_rate_sec=base,
        duration_sec=duration,
        captures=captures,
        captures_per_hour=captures / (duration / 3600.0) if duration else 0.0,
        insect_ticks=insect_ticks,
        insect_ticks_in_high=insect_in_high,
        coverage=(insect_in_high / insect_ticks) if insect_ticks else 1.0,
        high_ticks=high_ticks,
        false_high_ticks=false_high,
        false_high_rate=(false_high / non_insect) if non_insect else 0.0,
        missed_insect_ticks=insect_ticks - insect_in_high,
    )


def power_cost(metrics: PowerMetrics, weights: Optional[PowerObjectiveWeights] = None) -> float:
    """Single scalar cost to minimise: low energy, low false-HIGH, high coverage."""
    w = weights or PowerObjectiveWeights()
    return (
        w.energy_weight * metrics.captures_per_hour
        + w.false_high_weight * metrics.false_high_rate
        + w.miss_weight * (1.0 - metrics.coverage)
    )
