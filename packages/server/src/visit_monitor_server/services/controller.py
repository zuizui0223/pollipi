"""Timelapse controller for the active scheduled-mesh runtime."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from visit_monitor_server.config import (
    AUTONOMOUS_PATH,
    CAMERA_LABEL,
    CAMERA_MODEL,
    CAMERA_PROFILE,
    DEVICE_ID,
    DEVICE_NAME,
    IS_AI_CAMERA,
    IS_NOIR,
    IS_WIDE,
    USE_FAKE_CAMERA,
)

STOP_JOIN_TIMEOUT_SEC = 8.0


class TimelapseController:
    """Own camera lifecycle and expose lightweight status/preview state.

    Legacy ROI, ML, event-review, and training workflows are intentionally not
    part of this controller's active execution path.
    """

    def __init__(self, image_dir: Path) -> None:
        self.image_dir = image_dir
        self._lock = threading.Lock()
        self._camera_lock = threading.Lock()
        self._stop_event: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._camera = None
        self._monitor_stop_event: Optional[threading.Event] = None
        self._preview_subscriber_count = 0
        self._preview_producer_state = "idle"

        self.running = False
        self.lifecycle_state = "stopped"
        self.last_error: Optional[str] = None
        self.stop_timeout_sec = STOP_JOIN_TIMEOUT_SEC
        self.interval_sec: Optional[float] = None
        self.next_interval_sec: Optional[float] = None
        self.capture_count = 0
        self.last_capture_time: Optional[str] = None
        self.last_image: Optional[str] = None
        self.message = "Stopped."
        self.autonomous_mode = False
        self.adaptive_timelapse_mode = False
        self.mesh_shadow_mode = True
        self.interval_reason = "Scheduled interval."

        self.motion_score: Optional[float] = None
        self.changed_area_ratio: Optional[float] = None
        self.mean_brightness: Optional[float] = None
        self.brightness_delta: Optional[float] = None
        self.wind_like_motion = False
        self.num_blobs = 0
        self.largest_blob_area = 0
        self.largest_blob_ratio: Optional[float] = None
        self.small_blob_count = 0
        self.motion_type = "mesh_three_state"
        self.insect_candidate = False
        self.detection_count = 0
        self.event_count = 0

        self.site_id: Optional[str] = None
        self.flower_id: Optional[str] = None
        self.plant_species: Optional[str] = None
        self.observer: Optional[str] = None
        self.notes: Optional[str] = None
        self.comparison_session_id: Optional[str] = None
        self.camera_role: Optional[str] = None
        self.method_mode: Optional[str] = None

        self.mesh_decision: Optional[str] = None
        self.mesh_reason: Optional[str] = None
        self.mesh_active_cell_proportion: Optional[float] = None
        self.mesh_offset_agreement: Optional[float] = None
        self.mesh_global_synchrony: Optional[float] = None

    def _build_status(self):
        from visit_monitor_server.api.schemas.capture import StatusResponse

        # Fields retained below are compatibility values for the current schema.
        # Active clients use lifecycle, scheduled-image, interval, and mesh fields.
        return StatusResponse(
            running=self.running,
            lifecycle_state=self.lifecycle_state,
            last_error=self.last_error,
            preview_subscriber_count=self._preview_subscriber_count,
            preview_latest_frame_age_sec=None,
            preview_producer_state=self._preview_producer_state,
            interval_sec=self.interval_sec,
            next_interval_sec=self.next_interval_sec,
            capture_count=self.capture_count,
            last_capture_time=self.last_capture_time,
            last_image=self.last_image,
            message=self.message,
            auto_mode=False,
            motion_trigger_mode=False,
            hybrid_mode=False,
            ml_assist_mode=False,
            autonomous_mode=self.autonomous_mode,
            adaptive_timelapse_mode=self.adaptive_timelapse_mode,
            mesh_shadow_mode=self.mesh_shadow_mode,
            motion_score=self.motion_score,
            changed_area_ratio=self.changed_area_ratio,
            mean_brightness=self.mean_brightness,
            brightness_delta=self.brightness_delta,
            wind_like_motion=self.wind_like_motion,
            num_blobs=self.num_blobs,
            largest_blob_area=self.largest_blob_area,
            largest_blob_ratio=self.largest_blob_ratio,
            small_blob_count=self.small_blob_count,
            motion_type=self.motion_type,
            insect_candidate=self.insect_candidate,
            detection_count=self.detection_count,
            event_count=self.event_count,
            interval_reason=self.interval_reason,
            device_id=DEVICE_ID,
            device_name=DEVICE_NAME,
            camera_label=CAMERA_LABEL,
            camera_model=CAMERA_MODEL,
            camera_profile=CAMERA_PROFILE,
            is_ai_camera=IS_AI_CAMERA,
            is_noir=IS_NOIR,
            is_wide=IS_WIDE,
            site_id=self.site_id,
            flower_id=self.flower_id,
            plant_species=self.plant_species,
            observer=self.observer,
            notes=self.notes,
            comparison_session_id=self.comparison_session_id,
            camera_role=self.camera_role,
            method_mode=self.method_mode,
            roi_used=False,
            roi_x=None,
            roi_y=None,
            roi_w=None,
            roi_h=None,
            roi_semantics="whole_frame_overlapping_mesh",
            control_roi_used=False,
            control_roi_x=None,
            control_roi_y=None,
            control_roi_w=None,
            control_roi_h=None,
            floral_zone_score=None,
            background_control_score=None,
            zone_minus_control_score=None,
            grid_rows=0,
            grid_cols=0,
            changed_cell_count=0,
            changed_cell_ratio=self.changed_area_ratio,
            local_compactness=None,
            whole_frame_change_score=self.mesh_global_synchrony,
            previous_frame_elapsed_sec=None,
            robust_background_score=None,
            candidate_reasons=self.mesh_reason,
            mesh_decision=self.mesh_decision,
            mesh_reason=self.mesh_reason,
            mesh_active_cell_proportion=self.mesh_active_cell_proportion,
            mesh_offset_agreement=self.mesh_offset_agreement,
            mesh_global_synchrony=self.mesh_global_synchrony,
            roi_tracking=False,
            roi_tracking_success=False,
            roi_tracking_score=None,
            roi_search_margin=0,
            roi_tracking_min_score=0.0,
            initial_roi_x=None,
            initial_roi_y=None,
            initial_roi_w=None,
            initial_roi_h=None,
            tracked_roi_x=None,
            tracked_roi_y=None,
            tracked_roi_w=None,
            tracked_roi_h=None,
            roi_shift_x=None,
            roi_shift_y=None,
        )

    def status(self):
        with self._lock:
            return self._build_status()

    def status_unlocked(self):
        return self._build_status()

    def start(self, request):
        stopped = self.stop()
        if stopped.lifecycle_state == "stopping":
            with self._lock:
                self.message = "Previous timelapse is still stopping; start was not duplicated."
                return self.status_unlocked()

        if request.autonomous_mode:
            self._save_autonomous_request(request)

        stop_event = threading.Event()
        with self._lock:
            self.running = True
            self.lifecycle_state = "starting"
            self.last_error = None
            self.interval_sec = request.interval_sec
            self.next_interval_sec = request.interval_sec
            self.capture_count = 0
            self.last_capture_time = None
            self.last_image = None
            self.message = "Starting scheduled timelapse."
            self.autonomous_mode = request.autonomous_mode
            self.adaptive_timelapse_mode = False
            self.mesh_shadow_mode = True
            self.interval_reason = "Shadow mesh analysis; scheduled interval unchanged."
            self.motion_score = None
            self.changed_area_ratio = None
            self.mesh_decision = None
            self.mesh_reason = None
            self.mesh_active_cell_proportion = None
            self.mesh_offset_agreement = None
            self.mesh_global_synchrony = None
            self.site_id = request.site_id
            self.flower_id = request.flower_id
            self.plant_species = request.plant_species
            self.observer = request.observer
            self.notes = request.notes
            self.comparison_session_id = request.comparison_session_id
            self.camera_role = request.camera_role
            self.method_mode = request.method_mode
            self._stop_event = stop_event
            self._thread = threading.Thread(
                target=self._run_loop,
                args=(stop_event, request),
                name="pollipi-timelapse",
                daemon=True,
            )
            thread = self._thread

        thread.start()
        return self.status()

    def stop(self, preserve_autonomous: bool = False):
        self.stop_monitor()
        with self._lock:
            stop_event = self._stop_event
            thread = self._thread
            active = self.running or thread is not None
            if stop_event is not None:
                stop_event.set()
            if active:
                self.lifecycle_state = "stopping"

        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=self.stop_timeout_sec)

        with self._lock:
            if thread is not None and thread.is_alive():
                self.running = False
                self.lifecycle_state = "stopping"
                self.message = f"Stop requested; capture thread did not exit within {self.stop_timeout_sec:.0f}s."
                return self.status_unlocked()
            self.running = False
            self._stop_event = None
            self._thread = None
            self.lifecycle_state = "stopped"
            if not preserve_autonomous:
                self.autonomous_mode = False
            if active:
                self.message = "Timelapse stopped."
            status = self.status_unlocked()
        if not preserve_autonomous:
            self._clear_autonomous_request()
        return status

    def _run_loop(self, stop_event: threading.Event, request) -> None:
        from visit_monitor_server.services.capture_loop import run_capture_loop
        try:
            run_capture_loop(
                stop_event=stop_event,
                request=request,
                image_dir=self.image_dir,
                camera_lock=self._camera_lock,
                set_camera=self._set_camera,
                update_state=self._apply_state_update,
                set_message=self._set_message,
            )
        except Exception as exc:
            with self._lock:
                self.running = False
                self.lifecycle_state = "error"
                self.last_error = f"{type(exc).__name__}: {exc}"
                self.message = f"Capture loop failed: {exc}"
            raise
        finally:
            with self._lock:
                if self._thread is threading.current_thread() and self.lifecycle_state != "error":
                    self.running = False
                    self.lifecycle_state = "stopped"

    def _set_camera(self, camera) -> None:
        with self._lock:
            self._camera = camera
            if camera is not None:
                self.lifecycle_state = "running"
            else:
                self.running = False

    def _set_message(self, message: str) -> None:
        with self._lock:
            self.message = message

    def _apply_state_update(self, state: dict) -> None:
        with self._lock:
            if "interval_sec" in state:
                self.interval_sec = state["interval_sec"]
            if "next_interval_sec" in state:
                self.next_interval_sec = state["next_interval_sec"]
            if "message" in state:
                self.message = state["message"]
            if "motion_score" in state:
                self.motion_score = state["motion_score"]
            if "insect_candidate" in state:
                self.insect_candidate = bool(state["insect_candidate"])
            if "interval_reason" in state:
                self.interval_reason = state["interval_reason"]
            metrics = state.get("metrics")
            if metrics is not None:
                self.changed_area_ratio = metrics.get("changed_area_ratio")
                self.mean_brightness = metrics.get("mean_brightness")
                self.brightness_delta = metrics.get("brightness_delta")
                self.wind_like_motion = bool(metrics.get("wind_like_motion"))
                self.motion_type = str(metrics.get("motion_type") or "mesh_three_state")
                self.mesh_decision = metrics.get("mesh_decision")
                self.mesh_reason = metrics.get("mesh_reason")
                self.mesh_active_cell_proportion = metrics.get("mesh_active_cell_proportion")
                self.mesh_offset_agreement = metrics.get("mesh_offset_agreement")
                self.mesh_global_synchrony = metrics.get("mesh_global_synchrony")
            self.capture_count += state.get("capture_count_delta", 0)
            self.detection_count += state.get("detection_count_delta", 0)
            self.event_count += state.get("event_count_delta", 0)
            if state.get("last_capture_time") is not None:
                self.last_capture_time = state["last_capture_time"]
            if state.get("last_image") is not None:
                self.last_image = state["last_image"]

    def latest_image(self) -> Optional[Path]:
        with self._lock:
            image = self.last_image
        if image is None:
            return None
        path = Path(image)
        return path if path.is_file() else None

    def clear_latest_if_deleted(self, deleted_path: Optional[Path] = None) -> None:
        with self._lock:
            if deleted_path is None or self.last_image == str(deleted_path):
                self.last_image = None
                self.last_capture_time = None

    def preview_frame(self) -> bytes:
        image = self.latest_image()
        if image is None:
            raise RuntimeError("No scheduled image is available for preview.")
        return image.read_bytes()

    def stop_monitor(self) -> None:
        with self._lock:
            event = self._monitor_stop_event
            if event is not None:
                event.set()

    def monitor_frames(self, ai_detection: bool = False) -> Generator[bytes, None, None]:
        """Explicit one-viewer stream from scheduled images only.

        AI overlay is intentionally unsupported in the active runtime. The stream
        never opens a second camera and never competes with scheduled capture.
        """
        if ai_detection:
            raise RuntimeError("AI monitor is removed from the active workflow.")
        self.stop_monitor()
        stop_event = threading.Event()
        with self._lock:
            self._monitor_stop_event = stop_event
            self._preview_subscriber_count = 1
            self._preview_producer_state = "scheduled-image"
        try:
            last_path = None
            while not stop_event.is_set():
                image = self.latest_image()
                if image is not None:
                    path = str(image)
                    if path != last_path or last_path is None:
                        frame = image.read_bytes()
                        last_path = path
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                            + frame
                            + b"\r\n"
                        )
                if stop_event.wait(1.0):
                    break
        finally:
            with self._lock:
                if self._monitor_stop_event is stop_event:
                    self._monitor_stop_event = None
                self._preview_subscriber_count = 0
                self._preview_producer_state = "idle"

    def _save_autonomous_request(self, request) -> None:
        AUTONOMOUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        AUTONOMOUS_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _clear_autonomous_request(self) -> None:
        try:
            AUTONOMOUS_PATH.unlink(missing_ok=True)
        except Exception:
            pass

    def resume_autonomous(self) -> None:
        if not AUTONOMOUS_PATH.is_file():
            return
        try:
            from visit_monitor_server.api.schemas.capture import StartRequest
            data = json.loads(AUTONOMOUS_PATH.read_text(encoding="utf-8"))
            request = StartRequest(**data)
            if request.autonomous_mode:
                self.start(request)
        except Exception as exc:
            with self._lock:
                self.last_error = f"Autonomous resume failed: {exc}"
                self.message = self.last_error

    def migrate_legacy_candidates(self) -> None:
        """Compatibility hook retained for app startup; active runtime has no events."""
        return None
