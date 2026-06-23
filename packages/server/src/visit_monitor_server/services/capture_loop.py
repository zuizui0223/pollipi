"""Scheduled timelapse runtime with mesh shadow-mode metadata logging.

The active runtime saves scheduled timelapse images.  It uses the shared pure
``pollipi_analysis`` package to calculate an explainable three-state mesh decision
from low-resolution frames, but never claims a confirmed visit and never writes an
image-per-motion-event stream.
"""
from __future__ import annotations

import csv
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.policy.state_policy import IntervalBounds, plan_next_interval
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

        bounds = IntervalBounds(
            baseline_interval_sec=request.interval_sec,
            min_interval_sec=request.adaptive_min_interval_sec,
            max_interval_sec=request.adaptive_max_interval_sec,
        )

        while not stop_event.is_set():
            captured_at = datetime.now().astimezone()
            filename = captured_at.strftime("image_%Y%m%d_%H%M%S_%f.jpg")
            image_path = image_dir / filename

            with camera_lock:
                camera.capture_file(str(image_path))
                frame = camera.capture_array("lores")

            if previous_frame is None:
                would_be_next = request.interval_sec
                reason = "Mesh shadow mode: reference frame captured; scheduled interval unchanged."
                mesh_state: dict = {
                    "mesh_decision": "no_activity",
                    "mesh_reason": "waiting_for_reference_frame",
                    "mesh_active_cell_proportion": 0.0,
                    "mesh_offset_agreement": 0.0,
                    "mesh_global_synchrony": 0.0,
                }
            else:
                decision = analyze(
                    frame,
                    previous_frame,
                    previous_active_cells=previous_active_cells,
                    previous_centroid=previous_centroid,
                )
                plan = plan_next_interval(
                    decision.state,
                    bounds,
                    current_interval_sec=request.interval_sec,
                )
                would_be_next = plan.next_interval_sec
                reason = f"Mesh shadow mode: {decision.state}; {decision.reason}; scheduled interval unchanged."
                mesh_state = {
                    "mesh_decision": decision.state,
                    "mesh_reason": decision.reason,
                    "mesh_active_cell_proportion": decision.features.active_cell_proportion,
                    "mesh_offset_agreement": decision.features.offset_agreement,
                    "mesh_global_synchrony": decision.features.global_synchrony,
                }
                _write_shadow_record(
                    captured_at,
                    image_path,
                    request.interval_sec,
                    would_be_next,
                    decision,
                    request,
                )
                previous_active_cells = set(decision.active_cells)
                if decision.features.centroid_x is not None and decision.features.centroid_y is not None:
                    previous_centroid = (decision.features.centroid_x, decision.features.centroid_y)

            previous_frame = frame
            update_state({
                "capture_count_delta": 1,
                "interval_sec": request.interval_sec,
                "next_interval_sec": would_be_next,
                "last_capture_time": captured_at.isoformat(timespec="seconds"),
                "last_image": str(image_path),
                "message": "Scheduled timelapse running; shadow mesh analysis only.",
                "interval_reason": reason,
                **mesh_state,
            })

            # Adaptive control remains intentionally disabled until real Pi shadow
            # validation is complete.  The policy result is logged as would-be only.
            if stop_event.wait(request.interval_sec):
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
