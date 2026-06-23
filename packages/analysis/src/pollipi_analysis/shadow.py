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

from typing import Iterable, Optional, Sequence

from pollipi_analysis.pipeline import PipelineConfig
from pollipi_analysis.policy.state_policy import IntervalBounds, plan_next_interval
from pollipi_analysis.schemas.shadow import (
    DEFAULT_POLICY_NAME,
    DEFAULT_POLICY_VERSION,
    DEFAULT_VALIDATION_STATUS,
    ShadowDecisionRecord,
)
from pollipi_analysis.track import DEFAULT_TRACK_WINDOW, Tracker


def run_shadow_mode(
    frames: Iterable,
    *,
    bounds: IntervalBounds,
    current_interval_sec: Optional[float] = None,
    config: Optional[PipelineConfig] = None,
    device_id: str = "",
    timestamps: Optional[Sequence[str]] = None,
    track_window: int = DEFAULT_TRACK_WINDOW,
    policy_name: str = DEFAULT_POLICY_NAME,
    policy_version: str = DEFAULT_POLICY_VERSION,
    validation_status: str = DEFAULT_VALIDATION_STATUS,
) -> list[ShadowDecisionRecord]:
    cfg = config or PipelineConfig()
    frame_list = list(frames)
    records: list[ShadowDecisionRecord] = []

    interval = current_interval_sec if current_interval_sec is not None else bounds.baseline_interval_sec
    # The Tracker owns the centroid window and previous-frame state, so the Pi
    # capture loop and this simulation runner compute identical trajectory
    # features and decisions from the same frame sequence.
    tracker = Tracker(track_window=track_window, config=cfg)

    for index in range(1, len(frame_list)):
        background = frame_list[index - 1]
        frame = frame_list[index]
        decision = tracker.observe(frame, background)

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

    return records
