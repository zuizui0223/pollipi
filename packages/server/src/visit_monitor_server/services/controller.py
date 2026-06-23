"""Controller for PolliPi's scheduled-image mesh-shadow runtime."""
from __future__ import annotations

import json
import threading
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
)

STOP_JOIN_TIMEOUT_SEC = 8.0


class TimelapseController:
    """Own scheduled capture lifecycle and minimal status state.

    The active runtime has no ROI, tracking, ML, event queue, or per-motion image
    workflow. Preview and MJPEG expose only the most recently scheduled image.
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
        self.interval_reason = "Scheduled interval; shadow analysis only."

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

        return StatusResponse(
            device_id=DEVICE_ID,
            device_name=DEVICE_NAME,
            camera_label=CAMERA_LABEL,
            camera_model=CAMERA_MODEL,
            camera_profile=CAMERA_PROFILE,
            is_ai_camera=IS_AI_CAMERA,
            is_noir=IS_NOIR,
            is_wide=IS_WIDE,
            running=self.running,
            lifecycle_state=self.lifecycle_state,
            last_error=self.last_error,
            preview_subscriber_count=self._preview_subscriber_count,
            preview_latest_frame_age_sec=None,
            preview_producer_state="scheduled-image" if self._preview_subscriber_count else "idle",
            interval_sec=self.interval_sec,
            next_interval_sec=self.next_interval_sec,
            capture_count=self.capture_count,
            last_capture_time=self.last_capture_time,
            last_image=self.last_image,
            message=self.message,
            autonomous_mode=self.autonomous_mode,
            adaptive_timelapse_mode=self.adaptive_timelapse_mode,
            mesh_shadow_mode=self.mesh_shadow_mode,
            interval_reason=self.interval_reason,
            site_id=self.site_id,
            flower_id=self.flower_id,
            plant_species=self.plant_species,
            observer=self.observer,
            notes=self.notes,
            comparison_session_id=self.comparison_session_id,
            camera_role=self.camera_role,
            method_mode=self.method_mode,
            mesh_decision=self.mesh_decision,
            mesh_reason=self.mesh_reason,
            mesh_active_cell_proportion=self.mesh_active_cell_proportion,
            mesh_offset_agreement=self.mesh_offset_agreement,
            mesh_global_synchrony=self.mesh_global_synchrony,
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
            self.message = "Starting scheduled timelapse with mesh shadow logging."
            self.autonomous_mode = request.autonomous_mode
            # Live adaptive timing is intentionally disabled until real-Pi shadow
            # validation is complete, regardless of a historical client setting.
            self.adaptive_timelapse_mode = False
            self.mesh_shadow_mode = True
            self.interval_reason = "Shadow mesh analysis; scheduled interval unchanged."
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
            if "interval_reason" in state:
                self.interval_reason = state["interval_reason"]

            metrics = state.get("metrics") or {}
            self.mesh_decision = metrics.get("mesh_decision", self.mesh_decision)
            self.mesh_reason = metrics.get("mesh_reason", self.mesh_reason)
            self.mesh_active_cell_proportion = metrics.get(
                "mesh_active_cell_proportion", self.mesh_active_cell_proportion
            )
            self.mesh_offset_agreement = metrics.get(
                "mesh_offset_agreement", self.mesh_offset_agreement
            )
            self.mesh_global_synchrony = metrics.get(
                "mesh_global_synchrony", self.mesh_global_synchrony
            )

            self.capture_count += state.get("capture_count_delta", 0)
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
            if self._monitor_stop_event is not None:
                self._monitor_stop_event.set()
                self._monitor_stop_event = None

    def monitor_frames(self, ai_detection: bool = False) -> Generator[bytes, None, None]:
        """Serve a single explicit stream of scheduled images.

        This deliberately never opens a second camera or runs AI inference. A viewer
        receives the most recent saved image when it changes and a heartbeat frame
        thereafter, while scheduled capture remains the sole camera owner.
        """
        if ai_detection:
            raise RuntimeError("AI monitor is removed from the active workflow.")

        self.stop_monitor()
        stop_event = threading.Event()
        with self._lock:
            self._monitor_stop_event = stop_event
            self._preview_subscriber_count += 1

        last_path: Optional[str] = None
        try:
            while not stop_event.is_set():
                image = self.latest_image()
                if image is not None:
                    path = str(image)
                    if path != last_path:
                        frame = image.read_bytes()
                        last_path = path
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                            + frame
                            + b"\r\n"
                        )
                if stop_event.wait(0.8):
                    break
        finally:
            with self._lock:
                self._preview_subscriber_count = max(0, self._preview_subscriber_count - 1)
                if self._monitor_stop_event is stop_event:
                    self._monitor_stop_event = None

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
        """Compatibility startup hook; active runtime has no candidate queue."""
        return None
