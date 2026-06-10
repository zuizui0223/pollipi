"""Standalone capture loop function.

The loop body is extracted here so it can be tested independently of
``TimelapseController``.  The controller calls ``run_capture_loop``
inside a daemon thread.
"""
from __future__ import annotations

import csv
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from visit_monitor_server.config import (
    DEVICE_ID, DEVICE_NAME,
    CAMERA_LABEL, CAMERA_MODEL, CAMERA_PROFILE,
    IS_AI_CAMERA, IS_NOIR, IS_WIDE,
    METRICS_PATH, OBSERVATION_LOG_PATH,
    MONITOR_SIZE,
    MODEL_PATH,
    USE_FAKE_CAMERA,
)
from visit_monitor_server.services.motion import detect_motion
from visit_monitor_server.services.roi_tracking import (
    new_roi_tracker,
    tracking_roi_for_frame,
    tracking_metrics,
)

if TYPE_CHECKING:
    from visit_monitor_server.api.schemas.capture import StartRequest


def _metric_value(metrics: dict, key: str):
    value = metrics.get(key)
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return value


def _open_camera():
    """Return a started camera (FakeCamera or Picamera2)."""
    if USE_FAKE_CAMERA:
        from visit_monitor_server.adapters.fake_camera import FakeCamera
        return FakeCamera()
    from picamera2 import Picamera2  # type: ignore
    return Picamera2()


def _label_captured_image(image_path: Path, motion_label: str, ml_assist_mode: bool, trainer) -> None:
    from visit_monitor_server.services.image_store import register_label
    label = motion_label
    source = "motion_auto"
    if ml_assist_mode and MODEL_PATH.is_file():
        predicted = trainer.predict(image_path)
        if predicted is not None:
            label = predicted
            source = "field_ml_prediction"
    register_label(image_path, label, source)


def _write_metric(
    captured_at: datetime,
    image_path: Optional[Path],
    interval_sec: float,
    score: Optional[float],
    metrics: dict,
    insect_candidate: bool,
    reason: str,
    request,
) -> None:
    write_header = not METRICS_PATH.exists()
    with METRICS_PATH.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if write_header:
            writer.writerow([
                "timestamp", "image_filename", "interval_sec", "motion_score", "insect_candidate", "reason",
                "device_id", "device_name", "camera_label", "camera_model", "camera_profile",
                "is_ai_camera", "is_noir", "is_wide",
                "site_id", "flower_id", "plant_species", "observer", "notes",
                "comparison_session_id", "camera_role", "method_mode",
                "changed_area_ratio", "mean_brightness", "brightness_delta", "wind_like_motion",
                "num_blobs", "largest_blob_area", "largest_blob_ratio", "small_blob_count", "motion_type",
                "roi_used", "roi_x", "roi_y", "roi_w", "roi_h",
                "roi_tracking", "roi_tracking_success", "roi_tracking_score", "roi_search_margin",
                "roi_tracking_min_score", "initial_roi_x", "initial_roi_y", "initial_roi_w", "initial_roi_h",
                "tracked_roi_x", "tracked_roi_y", "tracked_roi_w", "tracked_roi_h", "roi_shift_x", "roi_shift_y",
            ])
        writer.writerow([
            captured_at.isoformat(timespec="seconds"),
            "" if image_path is None else image_path.name,
            interval_sec,
            "" if score is None else f"{score:.6f}",
            insect_candidate,
            reason,
            DEVICE_ID, DEVICE_NAME, CAMERA_LABEL, CAMERA_MODEL, CAMERA_PROFILE,
            IS_AI_CAMERA, IS_NOIR, IS_WIDE,
            "" if request is None or request.site_id is None else request.site_id,
            "" if request is None or request.flower_id is None else request.flower_id,
            "" if request is None or request.plant_species is None else request.plant_species,
            "" if request is None or request.observer is None else request.observer,
            "" if request is None or request.notes is None else request.notes,
            "" if request is None or request.comparison_session_id is None else request.comparison_session_id,
            "" if request is None or request.camera_role is None else request.camera_role,
            "" if request is None or request.method_mode is None else request.method_mode,
            _metric_value(metrics, "changed_area_ratio"),
            _metric_value(metrics, "mean_brightness"),
            _metric_value(metrics, "brightness_delta"),
            bool(metrics.get("wind_like_motion")),
            _metric_value(metrics, "num_blobs"),
            _metric_value(metrics, "largest_blob_area"),
            _metric_value(metrics, "largest_blob_ratio"),
            _metric_value(metrics, "small_blob_count"),
            _metric_value(metrics, "motion_type"),
            bool(metrics.get("roi_used")),
            _metric_value(metrics, "roi_x"),
            _metric_value(metrics, "roi_y"),
            _metric_value(metrics, "roi_w"),
            _metric_value(metrics, "roi_h"),
            bool(metrics.get("roi_tracking")),
            bool(metrics.get("roi_tracking_success")),
            _metric_value(metrics, "roi_tracking_score"),
            _metric_value(metrics, "roi_search_margin"),
            _metric_value(metrics, "roi_tracking_min_score"),
            _metric_value(metrics, "initial_roi_x"),
            _metric_value(metrics, "initial_roi_y"),
            _metric_value(metrics, "initial_roi_w"),
            _metric_value(metrics, "initial_roi_h"),
            _metric_value(metrics, "tracked_roi_x"),
            _metric_value(metrics, "tracked_roi_y"),
            _metric_value(metrics, "tracked_roi_w"),
            _metric_value(metrics, "tracked_roi_h"),
            _metric_value(metrics, "roi_shift_x"),
            _metric_value(metrics, "roi_shift_y"),
        ])


def _write_observation_event(
    captured_at: datetime,
    image_path: Optional[Path],
    capture_type: str,
    scheduled_interval_sec: float,
    scan_interval_sec: float,
    score: Optional[float],
    metrics: dict,
    insect_candidate: bool,
    reason: str,
    request,
) -> None:
    write_header = not OBSERVATION_LOG_PATH.exists()
    with OBSERVATION_LOG_PATH.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if write_header:
            writer.writerow([
                "timestamp", "capture_type", "image_filename",
                "scheduled_interval_sec", "scan_interval_sec",
                "motion_score", "motion_candidate", "reason",
                "device_id", "device_name", "camera_label", "camera_model", "camera_profile",
                "is_ai_camera", "is_noir", "is_wide",
                "site_id", "flower_id", "plant_species", "observer", "notes",
                "comparison_session_id", "camera_role", "method_mode",
                "changed_area_ratio", "mean_brightness", "brightness_delta", "wind_like_motion",
                "num_blobs", "largest_blob_area", "largest_blob_ratio", "small_blob_count", "motion_type",
                "roi_used", "roi_x", "roi_y", "roi_w", "roi_h",
                "roi_tracking", "roi_tracking_success", "roi_tracking_score", "roi_search_margin",
                "roi_tracking_min_score", "initial_roi_x", "initial_roi_y", "initial_roi_w", "initial_roi_h",
                "tracked_roi_x", "tracked_roi_y", "tracked_roi_w", "tracked_roi_h", "roi_shift_x", "roi_shift_y",
            ])
        writer.writerow([
            captured_at.isoformat(timespec="seconds"),
            capture_type,
            "" if image_path is None else image_path.name,
            scheduled_interval_sec,
            scan_interval_sec,
            "" if score is None else f"{score:.6f}",
            insect_candidate,
            reason,
            DEVICE_ID, DEVICE_NAME, CAMERA_LABEL, CAMERA_MODEL, CAMERA_PROFILE,
            IS_AI_CAMERA, IS_NOIR, IS_WIDE,
            "" if request.site_id is None else request.site_id,
            "" if request.flower_id is None else request.flower_id,
            "" if request.plant_species is None else request.plant_species,
            "" if request.observer is None else request.observer,
            "" if request.notes is None else request.notes,
            "" if request.comparison_session_id is None else request.comparison_session_id,
            "" if request.camera_role is None else request.camera_role,
            "" if request.method_mode is None else request.method_mode,
            _metric_value(metrics, "changed_area_ratio"),
            _metric_value(metrics, "mean_brightness"),
            _metric_value(metrics, "brightness_delta"),
            bool(metrics.get("wind_like_motion")),
            _metric_value(metrics, "num_blobs"),
            _metric_value(metrics, "largest_blob_area"),
            _metric_value(metrics, "largest_blob_ratio"),
            _metric_value(metrics, "small_blob_count"),
            _metric_value(metrics, "motion_type"),
            bool(metrics.get("roi_used")),
            _metric_value(metrics, "roi_x"),
            _metric_value(metrics, "roi_y"),
            _metric_value(metrics, "roi_w"),
            _metric_value(metrics, "roi_h"),
            bool(metrics.get("roi_tracking")),
            bool(metrics.get("roi_tracking_success")),
            _metric_value(metrics, "roi_tracking_score"),
            _metric_value(metrics, "roi_search_margin"),
            _metric_value(metrics, "roi_tracking_min_score"),
            _metric_value(metrics, "initial_roi_x"),
            _metric_value(metrics, "initial_roi_y"),
            _metric_value(metrics, "initial_roi_w"),
            _metric_value(metrics, "initial_roi_h"),
            _metric_value(metrics, "tracked_roi_x"),
            _metric_value(metrics, "tracked_roi_y"),
            _metric_value(metrics, "tracked_roi_w"),
            _metric_value(metrics, "tracked_roi_h"),
            _metric_value(metrics, "roi_shift_x"),
            _metric_value(metrics, "roi_shift_y"),
        ])


def _write_event_log(
    captured_at: datetime,
    image_path: Optional[Path],
    metrics: dict,
    request,
) -> None:
    from visit_monitor_server.config import EVENT_LOG_COLUMNS, EVENT_LOG_PATH

    write_header = not EVENT_LOG_PATH.exists()
    with EVENT_LOG_PATH.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if write_header:
            writer.writerow(EVENT_LOG_COLUMNS)
        writer.writerow([
            f"event_{captured_at.strftime('%Y%m%d_%H%M%S_%f')}_{DEVICE_ID}",
            captured_at.isoformat(timespec="seconds"),
            "" if image_path is None else image_path.name,
            DEVICE_ID, DEVICE_NAME, CAMERA_LABEL, CAMERA_MODEL, CAMERA_PROFILE,
            IS_AI_CAMERA, IS_NOIR, IS_WIDE,
            "" if request.site_id is None else request.site_id,
            "" if request.flower_id is None else request.flower_id,
            "" if request.plant_species is None else request.plant_species,
            "" if request.observer is None else request.observer,
            "" if request.notes is None else request.notes,
            "" if request.comparison_session_id is None else request.comparison_session_id,
            "" if request.camera_role is None else request.camera_role,
            "" if request.method_mode is None else request.method_mode,
            _metric_value(metrics, "motion_score"),
            _metric_value(metrics, "changed_area_ratio"),
            _metric_value(metrics, "mean_brightness"),
            _metric_value(metrics, "brightness_delta"),
            bool(metrics.get("wind_like_motion")),
            _metric_value(metrics, "num_blobs"),
            _metric_value(metrics, "largest_blob_area"),
            _metric_value(metrics, "largest_blob_ratio"),
            _metric_value(metrics, "small_blob_count"),
            _metric_value(metrics, "motion_type"),
            bool(metrics.get("roi_used")),
            _metric_value(metrics, "roi_x"),
            _metric_value(metrics, "roi_y"),
            _metric_value(metrics, "roi_w"),
            _metric_value(metrics, "roi_h"),
            bool(metrics.get("roi_tracking")),
            bool(metrics.get("roi_tracking_success")),
            _metric_value(metrics, "roi_tracking_score"),
            _metric_value(metrics, "roi_search_margin"),
            _metric_value(metrics, "roi_tracking_min_score"),
            _metric_value(metrics, "initial_roi_x"),
            _metric_value(metrics, "initial_roi_y"),
            _metric_value(metrics, "initial_roi_w"),
            _metric_value(metrics, "initial_roi_h"),
            _metric_value(metrics, "tracked_roi_x"),
            _metric_value(metrics, "tracked_roi_y"),
            _metric_value(metrics, "tracked_roi_w"),
            _metric_value(metrics, "tracked_roi_h"),
            _metric_value(metrics, "roi_shift_x"),
            _metric_value(metrics, "roi_shift_y"),
            "", "", "", "", "",  # manual fields
        ])


def _roi_tuple(request) -> Optional[tuple[int, int, int, int]]:
    if None in (request.roi_x, request.roi_y, request.roi_w, request.roi_h):
        return None
    return (int(request.roi_x), int(request.roi_y), int(request.roi_w), int(request.roi_h))


def _detect_motion_with_tracking(
    frame,
    background,
    pixel_difference: int,
    motion_ratio: float,
    roi: Optional[tuple[int, int, int, int]],
    roi_tracker: Optional[dict],
    request,
):
    active_roi = (
        tracking_roi_for_frame(
            frame, roi_tracker,
            request.roi_search_margin,
            request.roi_tracking_min_score,
        )
        if roi_tracker
        else roi
    )
    metrics, detected, background = detect_motion(
        frame, background, pixel_difference, motion_ratio, active_roi
    )
    metrics.update(tracking_metrics(roi_tracker, active_roi, request.roi_search_margin, request.roi_tracking_min_score))
    return metrics, detected, background


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

import time  # noqa: E402


def run_capture_loop(
    stop_event: threading.Event,
    request,
    image_dir: Path,
    camera_lock: threading.Lock,
    set_camera,          # callable(camera_or_None)
    update_state,        # callable(dict)  – thread-safe state updates
    set_message,         # callable(str)
    trainer,
) -> None:
    """
    The timelapse capture loop, now as a standalone function.

    Parameters
    ----------
    stop_event:
        Set to request loop termination.
    request:
        ``StartRequest`` pydantic model.
    image_dir:
        Where captured images are written.
    camera_lock:
        Shared lock for camera access.
    set_camera:
        Called with the live camera object (or ``None`` on teardown).
    update_state:
        Called with a dict of state fields to apply to the controller.
    set_message:
        Called with a status message string.
    trainer:
        ``BinaryTrainer`` instance for ML-assist mode.
    """
    camera = None
    background = None
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
        roi = _roi_tuple(request)
        roi_tracker = new_roi_tracker(roi, bool(request.roi_tracking and roi is not None))

        # Allow AE / AWB to settle
        if stop_event.wait(2):
            return

        set_message("Timelapse running.")

        import time as _time

        next_scheduled_time = _time.monotonic()
        while not stop_event.is_set():
            captured_at = datetime.now().astimezone()

            # ---- Hybrid mode ------------------------------------------------
            if request.hybrid_mode:
                with camera_lock:
                    frame = camera.capture_array("lores")
                metrics, insect_candidate, background = _detect_motion_with_tracking(
                    frame, background,
                    request.pixel_difference, request.motion_ratio,
                    roi, roi_tracker, request,
                )
                score = metrics["motion_score"]
                check_time = _time.monotonic()
                scheduled_due = check_time >= next_scheduled_time
                image_path = None
                capture_type = "none"
                if scheduled_due:
                    capture_type = "scheduled_event" if insect_candidate else "scheduled"
                    filename = captured_at.strftime(f"{capture_type}_%Y%m%d_%H%M%S_%f.jpg")
                    image_path = image_dir / filename
                    with camera_lock:
                        camera.capture_file(str(image_path))
                    while next_scheduled_time <= check_time:
                        next_scheduled_time += request.interval_sec
                    interval_reason = (
                        "Scheduled image saved with motion candidate."
                        if insect_candidate
                        else "Scheduled image saved."
                    )
                elif insect_candidate:
                    capture_type = "event"
                    filename = captured_at.strftime("event_%Y%m%d_%H%M%S_%f.jpg")
                    image_path = image_dir / filename
                    with camera_lock:
                        camera.capture_file(str(image_path))
                    interval_reason = "Motion candidate detected; supplemental event image saved."
                elif score is None:
                    interval_reason = "Motion baseline captured; scheduled observation continues."
                else:
                    interval_reason = "No motion candidate; waiting for next scheduled image."

                _write_observation_event(
                    captured_at, image_path, capture_type,
                    request.interval_sec, request.detection_interval_sec,
                    score, metrics, insect_candidate, interval_reason, request,
                )
                if insect_candidate:
                    _write_event_log(captured_at, image_path, metrics, request)
                if image_path is not None:
                    _label_captured_image(
                        image_path,
                        "positive" if insect_candidate else "negative",
                        request.ml_assist_mode, trainer,
                    )
                update_state({
                    "interval_sec": request.interval_sec,
                    "message": "Research hybrid observation running.",
                    "motion_score": score,
                    "metrics": metrics,
                    "insect_candidate": insect_candidate,
                    "interval_reason": interval_reason,
                    "detection_count_delta": 1 if insect_candidate else 0,
                    "event_count_delta": 1 if insect_candidate else 0,
                    "capture_count_delta": 1 if image_path is not None else 0,
                    "last_capture_time": captured_at.isoformat(timespec="seconds") if image_path else None,
                    "last_image": str(image_path) if image_path else None,
                })
                if stop_event.wait(request.detection_interval_sec):
                    break
                continue

            # ---- Motion-trigger mode ----------------------------------------
            if request.motion_trigger_mode:
                with camera_lock:
                    frame = camera.capture_array("lores")
                metrics, insect_candidate, background = _detect_motion_with_tracking(
                    frame, background,
                    request.pixel_difference, request.motion_ratio,
                    roi, roi_tracker, request,
                )
                score = metrics["motion_score"]
                image_path = None
                if score is None:
                    interval_reason = "Motion-trigger baseline captured; waiting for change."
                elif insect_candidate:
                    filename = captured_at.strftime("motion_%Y%m%d_%H%M%S_%f.jpg")
                    image_path = image_dir / filename
                    with camera_lock:
                        camera.capture_file(str(image_path))
                    interval_reason = "Motion candidate detected; image saved."
                else:
                    interval_reason = "Monitoring motion; no image saved."
                _write_metric(
                    captured_at, image_path, request.detection_interval_sec,
                    score, metrics, insect_candidate, interval_reason, request,
                )
                if insect_candidate:
                    _write_event_log(captured_at, image_path, metrics, request)
                if image_path is not None:
                    _label_captured_image(image_path, "positive", request.ml_assist_mode, trainer)
                update_state({
                    "interval_sec": request.detection_interval_sec,
                    "message": "Motion-trigger observation running.",
                    "motion_score": score,
                    "metrics": metrics,
                    "insect_candidate": insect_candidate,
                    "interval_reason": interval_reason,
                    "capture_count_delta": 1 if image_path is not None else 0,
                    "detection_count_delta": 1 if image_path is not None else 0,
                    "event_count_delta": 1 if image_path is not None else 0,
                    "last_capture_time": captured_at.isoformat(timespec="seconds") if image_path else None,
                    "last_image": str(image_path) if image_path else None,
                })
                if stop_event.wait(request.detection_interval_sec):
                    break
                continue

            # ---- Standard / auto mode ---------------------------------------
            filename = captured_at.strftime("image_%Y%m%d_%H%M%S_%f.jpg")
            image_path = image_dir / filename
            with camera_lock:
                camera.capture_file(str(image_path))

            next_interval = request.interval_sec
            score = None
            insect_candidate = False
            interval_reason = "Manual interval."
            metrics_val: dict = {}
            if request.auto_mode:
                with camera_lock:
                    frame = camera.capture_array("lores")
                metrics_val, insect_candidate, background = _detect_motion_with_tracking(
                    frame, background,
                    request.pixel_difference, request.motion_ratio,
                    roi, roi_tracker, request,
                )
                score = metrics_val["motion_score"]
                if score is None:
                    next_interval = request.idle_interval_sec
                    interval_reason = "Background baseline captured."
                elif insect_candidate:
                    next_interval = request.detection_interval_sec
                    interval_reason = "Motion candidate detected."
                else:
                    next_interval = request.idle_interval_sec
                    interval_reason = "No motion candidate; power-saving interval."
                _write_metric(
                    captured_at, image_path, next_interval,
                    score, metrics_val, insect_candidate, interval_reason, request,
                )
                if insect_candidate:
                    _write_event_log(captured_at, image_path, metrics_val, request)
                _label_captured_image(
                    image_path,
                    "positive" if insect_candidate else "negative",
                    request.ml_assist_mode, trainer,
                )
            elif request.ml_assist_mode and MODEL_PATH.is_file():
                _label_captured_image(image_path, "negative", True, trainer)

            update_state({
                "capture_count_delta": 1,
                "interval_sec": next_interval,
                "last_capture_time": captured_at.isoformat(timespec="seconds"),
                "last_image": str(image_path),
                "message": "Timelapse running.",
                "motion_score": score,
                "metrics": metrics_val if request.auto_mode else None,
                "insect_candidate": insect_candidate,
                "detection_count_delta": 1 if insect_candidate else 0,
                "event_count_delta": 1 if insect_candidate else 0,
                "interval_reason": interval_reason,
            })

            if stop_event.wait(next_interval):
                break

    except Exception as exc:
        set_message(f"Capture error: {exc}")
    finally:
        if camera is not None:
            with camera_lock:
                try:
                    camera.stop()
                finally:
                    camera.close()
        set_camera(None)
