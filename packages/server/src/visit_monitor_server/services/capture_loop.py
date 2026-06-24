"""Scheduled timelapse runtime with mesh shadow-mode metadata logging.

The active runtime saves scheduled timelapse images.  It uses the shared pure
``pollipi_analysis`` package to calculate an explainable three-state mesh decision
from low-resolution frames, but never claims a confirmed visit and never writes an
image-per-motion-event stream.
"""
from __future__ import annotations

import csv
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pollipi_analysis.abtest import ab_step
from pollipi_analysis.policy.state_policy import IntervalBounds, plan_next_interval
from pollipi_analysis.policy.two_stage import TwoStageConfig, TwoStageController
from pollipi_analysis.track import Tracker
from visit_monitor_server.config import (
    ADAPTIVE_CONTROL_ENABLED,
    ADAPTIVE_DECISION_LOG_PATH,
    CAMERA_LABEL,
    CAMERA_MODEL,
    CAMERA_PROFILE,
    DEVICE_ID,
    DEVICE_NAME,
    IS_AI_CAMERA,
    IS_NOIR,
    IS_WIDE,
    METRICS_PATH,
    MONITOR_SIZE,
    SHADOW_AB_LOG_PATH,
    USE_FAKE_CAMERA,
)

if TYPE_CHECKING:
    from visit_monitor_server.api.schemas.capture import StartRequest


SHADOW_COLUMNS = [
    "timestamp",
    "image_filename",
    "current_interval_sec",
    "would_be_next_interval_sec",
    "applied",
    "mesh_decision",
    "mesh_reason",
    "active_cell_proportion",
    "largest_component_cells",
    "concentration",
    "spatial_concentration",
    "offset_agreement",
    "persistence",
    "centroid_x",
    "centroid_y",
    "centroid_displacement",
    "path_efficiency",
    "direction_reversal",
    "global_synchrony",
    "estimated_global_shift",
    "device_id",
    "device_name",
    "site_id",
    "flower_id",
    "plant_species",
    "observer",
    "notes",
    "comparison_session_id",
    "camera_role",
    "method_mode",
    "policy_name",
    "policy_version",
    "validation_status",
]


def _open_camera():
    if USE_FAKE_CAMERA:
        from visit_monitor_server.adapters.fake_camera import FakeCamera
        return FakeCamera()
    from picamera2 import Picamera2  # type: ignore
    return Picamera2()


def _write_shadow_record(
    captured_at: datetime,
    image_path: Path,
    current_interval_sec: float,
    would_be_next_interval_sec: float,
    decision,
    request,
    policy_meta=None,
    applied: bool = False,
) -> None:
    """Append compact scheduled-image metadata.  No candidate-event image exists.

    ``applied`` is False in shadow mode (timing unchanged). When live two-stage
    control is enabled it is True and ``would_be_next_interval_sec`` is the
    interval actually used for the next capture.
    """
    write_header = not METRICS_PATH.exists()
    features = decision.features
    with METRICS_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(SHADOW_COLUMNS)
        writer.writerow([
            captured_at.isoformat(timespec="seconds"),
            image_path.name,
            f"{current_interval_sec:.3f}",
            f"{would_be_next_interval_sec:.3f}",
            applied,
            decision.state,
            decision.reason,
            features.active_cell_proportion,
            features.largest_component_cells,
            features.concentration,
            features.spatial_concentration,
            features.offset_agreement,
            features.persistence,
            features.centroid_x,
            features.centroid_y,
            features.centroid_displacement,
            features.path_efficiency,
            features.direction_reversal,
            features.global_synchrony,
            features.estimated_global_shift,
            DEVICE_ID,
            DEVICE_NAME,
            request.site_id or "",
            request.flower_id or "",
            request.plant_species or "",
            request.observer or "",
            request.notes or "",
            request.comparison_session_id or "",
            request.camera_role or "",
            request.method_mode or "",
            getattr(policy_meta, "policy_name", "baseline_rule"),
            getattr(policy_meta, "policy_version", "0"),
            getattr(policy_meta, "validation_status", "synthetic_only"),
        ])

    decision_header = not ADAPTIVE_DECISION_LOG_PATH.exists()
    with ADAPTIVE_DECISION_LOG_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if decision_header:
            writer.writerow([
                "timestamp",
                "current_interval_sec",
                "would_be_next_interval_sec",
                "mesh_decision",
                "mesh_reason",
                "applied",
            ])
        writer.writerow([
            captured_at.isoformat(timespec="seconds"),
            f"{current_interval_sec:.3f}",
            f"{would_be_next_interval_sec:.3f}",
            decision.state,
            decision.reason,
            applied,
        ])


AB_COLUMNS = [
    "timestamp",
    "image_filename",
    "current_interval_sec",
    "a_policy_name",
    "a_policy_version",
    "a_state",
    "a_reason",
    "a_would_be_next_interval_sec",
    "b_policy_name",
    "b_policy_version",
    "b_state",
    "b_reason",
    "b_would_be_next_interval_sec",
    "agree",
    "b_more_aggressive",
    "a_more_aggressive",
    "device_id",
    "device_name",
    "comparison_session_id",
    "camera_role",
]


def _write_ab_record(
    captured_at: datetime,
    image_path: Path,
    current_interval_sec: float,
    decision_a,
    would_be_a: float,
    meta_a,
    decision_b,
    would_be_b: float,
    meta_b,
    request,
) -> None:
    """Append one per-frame baseline(A)-vs-simulation-informed(B) shadow comparison.

    Both decisions are computed on the SAME real frame; neither changes timing.
    The ``b_more_aggressive`` flag (B proposes a shorter next interval) is the key
    adoption signal: it is the extra power/review B would cost over the baseline.
    """
    cmp = ab_step(decision_a.state, would_be_a, decision_b.state, would_be_b)
    write_header = not SHADOW_AB_LOG_PATH.exists()
    with SHADOW_AB_LOG_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(AB_COLUMNS)
        writer.writerow([
            captured_at.isoformat(timespec="seconds"),
            image_path.name,
            f"{current_interval_sec:.3f}",
            getattr(meta_a, "policy_name", "baseline_rule"),
            getattr(meta_a, "policy_version", "0"),
            decision_a.state,
            decision_a.reason,
            f"{would_be_a:.3f}",
            getattr(meta_b, "policy_name", "baseline_rule"),
            getattr(meta_b, "policy_version", "0"),
            decision_b.state,
            decision_b.reason,
            f"{would_be_b:.3f}",
            cmp["agree"],
            cmp["b_more_aggressive"],
            cmp["a_more_aggressive"],
            DEVICE_ID,
            DEVICE_NAME,
            request.comparison_session_id or "",
            request.camera_role or "",
        ])


def run_capture_loop(
    stop_event: threading.Event,
    request,
    image_dir: Path,
    camera_lock: threading.Lock,
    set_camera,
    update_state,
    set_message,
    trainer=None,
) -> None:
    """Run scheduled capture and shadow-mode mesh analysis.

    ``trainer`` remains a no-op compatibility argument while older controller
    construction code is being removed.  The active runtime does not use ML.
    """
    del trainer
    camera = None
    previous_frame = None

    try:
        image_dir.mkdir(parents=True, exist_ok=True)
        with camera_lock:
            camera = _open_camera()
            camera.configure(
                camera.create_still_configuration(
                    lores={"size": MONITOR_SIZE, "format": "YUV420"}
                )
            )
            camera.start()
        set_camera(camera)

        if stop_event.wait(2):
            return
        set_message("Scheduled timelapse running; mesh decisions are logged in shadow mode.")

        bounds = IntervalBounds(
            baseline_interval_sec=request.interval_sec,
            min_interval_sec=request.adaptive_min_interval_sec,
            max_interval_sec=request.adaptive_max_interval_sec,
        )

        # Issue #21: load the (simulation-informed) policy artifact once. The Pi
        # only consumes numeric thresholds here — no simulation/search runs.
        # Phase 3: also load the built-in baseline so the two policies run side by
        # side in shadow on the same real frames (shadow A/B). When no artifact is
        # present, B == baseline and A/B logging is skipped.
        from visit_monitor_server.services.policy_runtime import get_ab_policies

        (baseline_config, baseline_meta), (policy_config, policy_meta), ab_enabled = get_ab_policies()

        # The Pi drives the SAME Tracker as the PC simulation shadow runner, so a
        # given frame sequence yields identical trajectory features and decisions.
        # B (active/candidate) drives the existing shadow log + status; A (baseline)
        # runs alongside only for the A/B comparison.
        tracker = Tracker(config=policy_config)
        tracker_baseline = Tracker(config=baseline_config) if ab_enabled else None
        if ab_enabled:
            set_message(
                "Scheduled timelapse running; shadow A/B "
                f"(A={baseline_meta.policy_name} vs B={policy_meta.policy_name})."
            )

        # Phase 4: live two-stage LOW/HIGH control, off unless explicitly enabled
        # (per-session request flag or the POLLIPI_ADAPTIVE_CONTROL env switch).
        # When on, the active (B) policy's decision drives real capture timing;
        # otherwise the loop keeps the fixed interval and only logs would-be.
        control_enabled = bool(getattr(request, "two_stage_control", False) or ADAPTIVE_CONTROL_ENABLED)
        controller = (
            TwoStageController(
                config=TwoStageConfig(
                    low_rate_sec=request.low_rate_sec,
                    high_rate_sec=request.high_rate_sec,
                    high_hold_sec=request.high_hold_sec,
                )
            )
            if control_enabled
            else None
        )
        if control_enabled:
            set_message(
                "Two-stage LOW/HIGH control ENABLED "
                f"(LOW={request.low_rate_sec:g}s HIGH={request.high_rate_sec:g}s "
                f"hold={request.high_hold_sec:g}s)."
            )

        while not stop_event.is_set():
            captured_at = datetime.now().astimezone()
            filename = captured_at.strftime("image_%Y%m%d_%H%M%S_%f.jpg")
            image_path = image_dir / filename

            with camera_lock:
                camera.capture_file(str(image_path))
                frame = camera.capture_array("lores")

            if previous_frame is None:
                # Reference frame: no decision yet. Start at LOW under live control,
                # otherwise hold the requested interval.
                next_sleep = controller.config.low_rate_sec if controller else request.interval_sec
                would_be_next = next_sleep
                applied = control_enabled
                reason = "Reference frame captured; awaiting first analysed pair."
                mesh_state: dict = {
                    "mesh_decision": "no_activity",
                    "mesh_reason": "waiting_for_reference_frame",
                    "mesh_active_cell_proportion": 0.0,
                    "mesh_offset_agreement": 0.0,
                    "mesh_global_synchrony": 0.0,
                    "two_stage_mode": (controller.mode if controller else None),
                    "adaptive_control": control_enabled,
                }
            else:
                decision = tracker.observe(frame, previous_frame)
                # Continuous would-be interval, kept for the shadow log + A/B
                # comparison regardless of whether live control is on.
                plan = plan_next_interval(
                    decision.state,
                    bounds,
                    current_interval_sec=request.interval_sec,
                )

                if controller is not None:
                    step = controller.step(decision.state, now_sec=time.monotonic())
                    next_sleep = step.interval_sec
                    would_be_next = step.interval_sec
                    applied = True
                    mode = step.mode
                    reason = (
                        f"Two-stage {mode}: {decision.state}; {decision.reason}; "
                        f"interval={step.interval_sec:g}s."
                    )
                else:
                    next_sleep = request.interval_sec
                    would_be_next = plan.next_interval_sec
                    applied = False
                    mode = None
                    reason = (
                        f"Mesh shadow mode: {decision.state}; {decision.reason}; "
                        "scheduled interval unchanged."
                    )

                mesh_state = {
                    "mesh_decision": decision.state,
                    "mesh_reason": decision.reason,
                    "mesh_active_cell_proportion": decision.features.active_cell_proportion,
                    "mesh_offset_agreement": decision.features.offset_agreement,
                    "mesh_global_synchrony": decision.features.global_synchrony,
                    "two_stage_mode": mode,
                    "adaptive_control": control_enabled,
                }
                _write_shadow_record(
                    captured_at,
                    image_path,
                    request.interval_sec,
                    would_be_next,
                    decision,
                    request,
                    policy_meta,
                    applied=applied,
                )

                if tracker_baseline is not None:
                    decision_a = tracker_baseline.observe(frame, previous_frame)
                    plan_a = plan_next_interval(
                        decision_a.state,
                        bounds,
                        current_interval_sec=request.interval_sec,
                    )
                    # The A/B log compares the two classifiers under the same
                    # (continuous) interval mapping, so it stays meaningful whether
                    # or not live two-stage control is applied.
                    _write_ab_record(
                        captured_at,
                        image_path,
                        request.interval_sec,
                        decision_a,
                        plan_a.next_interval_sec,
                        baseline_meta,
                        decision,
                        plan.next_interval_sec,
                        policy_meta,
                        request,
                    )

            previous_frame = frame
            update_state({
                "capture_count_delta": 1,
                "interval_sec": request.interval_sec,
                "next_interval_sec": would_be_next,
                "last_capture_time": captured_at.isoformat(timespec="seconds"),
                "last_image": str(image_path),
                "message": (
                    "Two-stage LOW/HIGH control active."
                    if control_enabled
                    else "Scheduled timelapse running; shadow mesh analysis only."
                ),
                "interval_reason": reason,
                **mesh_state,
            })

            # Under live control the next interval is the two-stage decision;
            # otherwise it stays the fixed scheduled interval (shadow only).
            if stop_event.wait(next_sleep):
                break

    except Exception as exc:
        set_message(f"Capture error: {exc}")
        raise
    finally:
        if camera is not None:
            with camera_lock:
                try:
                    camera.stop()
                finally:
                    camera.close()
        set_camera(None)
