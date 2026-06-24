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
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.policy import create_policy_controller, get_policy_profile
from visit_monitor_server.config import (
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
    PROBE_INTERVAL_SEC,
    PROBE_SHADOW_LOG_PATH,
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
    "policy_profile_id",
    "simulation_run_id",
    "kind",
    "live_allowed",
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
    policy_profile=None,
) -> None:
    """Append compact scheduled-image metadata.  No candidate-event image exists."""
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
            False,
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
            getattr(policy_profile, "profile_id", getattr(request, "policy_profile_id", "") or ""),
            getattr(policy_profile, "simulation_run_id", ""),
            getattr(policy_profile, "kind", ""),
            getattr(policy_profile, "live_allowed", False),
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
            False,
        ])


PROBE_SHADOW_COLUMNS = [
    "probe_timestamp",
    "probe_interval_sec",
    "would_be_mode",
    "would_be_interval_sec",
    "decision_state",
    "decision_reason",
    "local_candidate_streak",
    "quiet_streak",
    "high_elapsed_sec",
    "high_remaining_sec",
    "actual_highres_saved",
    "next_highres_due_at",
    "policy_name",
    "policy_version",
    "validation_status",
    "policy_profile_id",
    "simulation_run_id",
    "kind",
    "live_allowed",
]


def _write_probe_record(
    probe_at: datetime,
    probe_interval_sec: float,
    out,
    decision_state: str,
    decision_reason: str,
    actual_highres_saved: bool,
    next_highres_due_at: str,
    policy_meta,
    policy_profile,
) -> None:
    """Append one row per low-resolution probe (no image saved here)."""
    write_header = not PROBE_SHADOW_LOG_PATH.exists()
    with PROBE_SHADOW_LOG_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(PROBE_SHADOW_COLUMNS)
        writer.writerow([
            probe_at.isoformat(timespec="seconds"),
            f"{probe_interval_sec:.3f}",
            out.mode,
            f"{out.interval_sec:.3f}",
            decision_state,
            decision_reason,
            out.local_candidate_streak,
            out.quiet_streak,
            f"{out.high_elapsed_sec:.3f}",
            f"{out.high_remaining_sec:.3f}",
            actual_highres_saved,
            next_highres_due_at,
            getattr(policy_meta, "policy_name", "baseline_rule"),
            getattr(policy_meta, "policy_version", "0"),
            getattr(policy_meta, "validation_status", "synthetic_only"),
            policy_profile.profile_id,
            policy_profile.simulation_run_id,
            policy_profile.kind,
            policy_profile.live_allowed,
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
    previous_active_cells = None
    previous_centroid = None

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

        # Issue #21: load the (simulation-informed) policy artifact once. The Pi
        # only consumes numeric thresholds here — no simulation/search runs.
        from visit_monitor_server.services.policy_runtime import get_active_policy

        policy_config, policy_meta = get_active_policy()
        policy_profile = get_policy_profile(request.policy_profile_id)

        # Issue #27 probe-only three-stage shadow. Two clocks:
        #  - low-resolution probe every PROBE_INTERVAL_SEC (no JPEG saved),
        #  - high-resolution JPEG on the fixed scheduled interval.
        # The three-stage controller only logs a WOULD-BE mode; capture timing is
        # never changed (live adaptive control stays off).
        hires_interval = float(request.interval_sec)
        probe_interval = min(PROBE_INTERVAL_SEC, hires_interval)
        three = create_policy_controller(policy_profile)

        update_state({
            "probe_interval_sec": probe_interval,
            "would_be_mode": "LOW",
            "would_be_interval_sec": three.config.low_interval_sec,
            "policy_profile_id": policy_profile.profile_id,
            "simulation_run_id": policy_profile.simulation_run_id,
            "kind": policy_profile.kind,
            "live_allowed": policy_profile.live_allowed,
            "message": "Probe-only three-stage shadow; high-res capture fixed.",
        })

        start_mono = time.monotonic()
        next_hires_due = start_mono  # save the first high-res frame immediately

        while not stop_event.is_set():
            now_mono = time.monotonic()
            captured_at = datetime.now().astimezone()

            with camera_lock:
                frame = camera.capture_array("lores")

            if previous_frame is None:
                decision = None
                decision_state = "no_activity"
                decision_reason = "waiting_for_reference_frame"
            else:
                decision = analyze(
                    frame,
                    previous_frame,
                    config=policy_config,
                    previous_active_cells=previous_active_cells,
                    previous_centroid=previous_centroid,
                )
                decision_state = decision.state
                decision_reason = decision.reason
                previous_active_cells = set(decision.active_cells)
                if decision.features.centroid_x is not None and decision.features.centroid_y is not None:
                    previous_centroid = (decision.features.centroid_x, decision.features.centroid_y)
            previous_frame = frame

            out = three.step(decision_state, now_mono)

            # High-resolution JPEG on the fixed schedule only.
            actual_highres_saved = False
            if now_mono >= next_hires_due:
                filename = captured_at.strftime("image_%Y%m%d_%H%M%S_%f.jpg")
                image_path = image_dir / filename
                with camera_lock:
                    camera.capture_file(str(image_path))
                actual_highres_saved = True
                next_hires_due += hires_interval
                if next_hires_due <= now_mono:  # avoid drift after a slow cycle
                    next_hires_due = now_mono + hires_interval
                if decision is not None:
                    _write_shadow_record(
                        captured_at,
                        image_path,
                        hires_interval,
                        out.interval_sec,
                        decision,
                        request,
                        policy_meta,
                        policy_profile,
                    )
                update_state({
                    "capture_count_delta": 1,
                    "last_capture_time": captured_at.isoformat(timespec="seconds"),
                    "last_image": str(image_path),
                })

            next_due_at = (captured_at + timedelta(seconds=max(0.0, next_hires_due - now_mono))).isoformat(timespec="seconds")
            _write_probe_record(
                captured_at, probe_interval, out, decision_state, decision_reason,
                actual_highres_saved, next_due_at, policy_meta, policy_profile,
            )

            mesh_state = {
                "mesh_decision": decision_state,
                "mesh_reason": decision_reason,
                "mesh_active_cell_proportion": decision.features.active_cell_proportion if decision else 0.0,
                "mesh_offset_agreement": decision.features.offset_agreement if decision else 0.0,
                "mesh_global_synchrony": decision.features.global_synchrony if decision else 0.0,
            }
            update_state({
                "interval_sec": hires_interval,  # actual observed high-res capture gap
                "next_interval_sec": hires_interval,
                "would_be_mode": out.mode,
                "would_be_interval_sec": out.interval_sec,
                "policy_profile_id": policy_profile.profile_id,
                "simulation_run_id": policy_profile.simulation_run_id,
                "kind": policy_profile.kind,
                "live_allowed": policy_profile.live_allowed,
                "interval_reason": (
                    f"Probe shadow: would-be {out.mode} ({out.interval_sec:.0f}s); "
                    f"{decision_reason}; high-res fixed at {hires_interval:.0f}s."
                ),
                **mesh_state,
            })

            # Adaptive control remains intentionally disabled until real Pi shadow
            # validation is complete.  Only the probe cadence governs the loop.
            if stop_event.wait(probe_interval):
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
