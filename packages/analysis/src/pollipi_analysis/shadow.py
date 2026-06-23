"""Pure shadow-mode runner.

Replays a sequence of scheduled timelapse frames and, for each one, records what
the adaptive policy *would* have decided. It never changes capture timing and
never persists a per-motion image — it only emits :class:`ShadowDecisionRecord`
rows. The same feature and policy functions run here and on the Pi.

Background model: each scheduled frame is compared against the previous scheduled
frame (frame-to-frame on the fixed interval). This keeps shadow mode dependency
free; the Pi runtime can substitute a maintained reference frame if desired.
"""
from __future__ import annotations

import dataclasses
import math
from typing import Iterable, Optional, Sequence

from pollipi_analysis.pipeline import PipelineConfig, analyze
from pollipi_analysis.policy.state_policy import IntervalBounds, plan_next_interval
from pollipi_analysis.schemas.decision import MeshDecision
from pollipi_analysis.schemas.shadow import (
    DEFAULT_POLICY_NAME,
    DEFAULT_POLICY_VERSION,
    DEFAULT_VALIDATION_STATUS,
    ShadowDecisionRecord,
)


def _trajectory_features(
    centroids: Sequence[tuple[float, float]],
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Return ``(path_efficiency, mean_step, reversal_rate)`` over the track window.

    - ``path_efficiency``: net / total path length — ~1.0 for a directed traverse,
      ~0 for back-and-forth sway.
    - ``mean_step``: average centroid displacement between consecutive frames.
    - ``reversal_rate``: fraction of consecutive step-vector pairs that reverse
      direction (negative dot product) — high for oscillation.

    These are logged in shadow mode only; they do not drive the active decision.
    """
    pts = [p for p in centroids if p is not None]
    if len(pts) < 2:
        return None, None, None
    vectors = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    steps = [math.hypot(vx, vy) for vx, vy in vectors]
    mean_step = sum(steps) / len(steps)
    total = sum(steps)
    if total <= 1e-6:
        path_eff = 0.0
    else:
        net = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
        path_eff = float(net / total)
    rev_den = 0
    rev = 0
    for a, b in zip(vectors, vectors[1:]):
        if math.hypot(*a) > 1e-8 and math.hypot(*b) > 1e-8:
            rev_den += 1
            if (a[0] * b[0] + a[1] * b[1]) < 0:
                rev += 1
    reversal_rate = (rev / rev_den) if rev_den else 0.0
    return path_eff, float(mean_step), float(reversal_rate)


def run_shadow_mode(
    frames: Iterable,
    *,
    bounds: IntervalBounds,
    current_interval_sec: Optional[float] = None,
    config: Optional[PipelineConfig] = None,
    device_id: str = "",
    timestamps: Optional[Sequence[str]] = None,
    track_window: int = 6,
    policy_name: str = DEFAULT_POLICY_NAME,
    policy_version: str = DEFAULT_POLICY_VERSION,
    validation_status: str = DEFAULT_VALIDATION_STATUS,
) -> list[ShadowDecisionRecord]:
    cfg = config or PipelineConfig()
    frame_list = list(frames)
    records: list[ShadowDecisionRecord] = []

    interval = current_interval_sec if current_interval_sec is not None else bounds.baseline_interval_sec
    previous_active: Optional[set[tuple[int, int]]] = None
    previous_centroid: Optional[tuple[float, float]] = None
    centroid_window: list[tuple[float, float]] = []

    for index in range(1, len(frame_list)):
        background = frame_list[index - 1]
        frame = frame_list[index]
        decision = analyze(
            frame,
            background,
            config=cfg,
            previous_active_cells=previous_active,
            previous_centroid=previous_centroid,
        )

        centroid = _centroid_xy(decision)
        if centroid is not None:
            centroid_window.append(centroid)
            centroid_window[:] = centroid_window[-track_window:]
        path_eff, mean_step, reversal_rate = _trajectory_features(centroid_window)
        decision = _with_trajectory(decision, path_eff, mean_step, reversal_rate, len(centroid_window))
        if path_eff is not None:
            decision = _apply_track_evidence(decision, path_eff, len(centroid_window))

        plan = plan_next_interval(decision.state, bounds, current_interval_sec=interval)

        captured_at = (
            timestamps[index] if timestamps is not None and index < len(timestamps) else f"frame-{index}"
        )
        records.append(
            ShadowDecisionRecord(
                frame_index=index,
                captured_at=captured_at,
                current_interval_sec=float(interval),
                would_be_next_interval_sec=float(plan.next_interval_sec),
                decision=decision,
                activity_score=float(plan.activity_score),
                device_id=device_id,
                applied=False,  # shadow mode: timing is never changed
                policy_name=policy_name,
                policy_version=policy_version,
                validation_status=validation_status,
            )
        )

        # Shadow mode keeps the real fixed interval. We only advance the
        # hypothetical "current" interval for non-transient drift so the logged
        # would-be interval reflects gradual lengthening under no activity/noise.
        if not plan.transient:
            interval = plan.next_interval_sec
        previous_active = set(decision.active_cells)
        previous_centroid = centroid

    return records


#: A directed traverse keeps net/path near 1; oscillating sway drops well below.
TRACK_PATH_EFFICIENCY_FLOOR = 0.45


def _apply_track_evidence(decision: MeshDecision, path_efficiency: float, window_len: int) -> MeshDecision:
    """Downgrade a strong candidate that the track reveals to be oscillation.

    A single frame pair cannot tell a directed visitor from a swaying leaf; only
    several captures of low path efficiency can. Once the track window has enough
    points, a strong candidate with low path efficiency is reclassified as
    oscillation-driven environmental noise.
    """
    from pollipi_analysis.schemas.states import ENVIRONMENTAL_NOISE, STRONG_VISITATION_CANDIDATE

    if (
        decision.state == STRONG_VISITATION_CANDIDATE
        and window_len >= 3
        and path_efficiency < TRACK_PATH_EFFICIENCY_FLOOR
    ):
        return dataclasses.replace(
            decision, state=ENVIRONMENTAL_NOISE, reason="low_path_efficiency_oscillation"
        )
    return decision


def _centroid_xy(decision: MeshDecision) -> Optional[tuple[float, float]]:
    f = decision.features
    if f.centroid_x is None or f.centroid_y is None:
        return None
    return (f.centroid_x, f.centroid_y)


def _with_trajectory(
    decision: MeshDecision,
    path_efficiency: Optional[float],
    mean_step: Optional[float],
    reversal_rate: Optional[float],
    track_frames: int,
) -> MeshDecision:
    features = dataclasses.replace(
        decision.features,
        path_efficiency=path_efficiency,
        mean_step=mean_step,
        reversal_rate=reversal_rate,
        track_frames=track_frames,
    )
    return dataclasses.replace(decision, features=features)
