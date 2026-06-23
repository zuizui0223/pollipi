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
        # Monitor / preview producer fields (single producer)
        self._monitor_stop_event: Optional[threading.Event] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_lock = threading.Lock()
        self._latest_frame_bytes: Optional[bytes] = None
        self._preview_subscriber_count = 0
        self._preview_producer_state = "idle"
        self._monitor_idle_timeout = 6.0  # seconds: idle timeout before stopping producer

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
        from visit_monitor_server.services.policy_runtime import get_active_policy

        _policy_config, _policy_meta = get_active_policy()

        return StatusResponse(
            policy_name=_policy_meta.policy_name,
            policy_version=_policy_meta.policy_version,
            validation_status=_policy_meta.validation_status,
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
            autonomous_mode=self.autonomous_mode,
            adaptive_timelapse_mode=self.adaptive_timelapse_mode,
            mesh_shadow_mode=self.mesh_shadow_mode,
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
            self.message = "Starting scheduled timelapse."
            self.autonomous_mode = request.autonomous_mode
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
        # ensure monitor/producers are stopped before stopping capture
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
            if "mesh_decision" in state:
                self.mesh_decision = state["mesh_decision"]
            if "mesh_reason" in state:
                self.mesh_reason = state["mesh_reason"]
            if "mesh_active_cell_proportion" in state:
                self.mesh_active_cell_proportion = state["mesh_active_cell_proportion"]
            if "mesh_offset_agreement" in state:
                self.mesh_offset_agreement = state["mesh_offset_agreement"]
            if "mesh_global_synchrony" in state:
                self.mesh_global_synchrony = state["mesh_global_synchrony"]
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
        """Return a preview JPEG bytes.

        Prefer the producer cache if available (non-blocking). If no cached latest
        frame exists, fall back to the scheduled latest image on disk. We avoid
        opening a camera instance here to prevent lifecycle conflicts with
        /mjpeg and the capture loop.
        """
        # Prefer the in-memory producer cache
        with self._monitor_lock:
            if self._latest_frame_bytes is not None:
                return self._latest_frame_bytes

        # Fall back to the last scheduled image on disk
        image = self.latest_image()
        if image is not None:
            return image.read_bytes()

        # No scheduled image available; raise a consistent error so the router
        # can turn it into a 503. Don't attempt to open the camera here which can
        # cause acquisition conflicts with the monitor producer.
        raise RuntimeError("No scheduled image is available for preview.")

    def stop_monitor(self) -> None:
        with self._lock:
            event = self._monitor_stop_event
            if event is not None:
                event.set()
        # Also stop the dedicated monitor producer if any
        self._stop_monitor_producer()

    def _start_monitor_producer(self) -> None:
        with self._monitor_lock:
            if self._monitor_thread is not None and self._monitor_thread.is_alive():
                return
            stop_event = threading.Event()
            thread = threading.Thread(target=self._monitor_loop, args=(stop_event,), name="pollipi-monitor", daemon=True)
            self._monitor_thread = thread
            self._monitor_stop_event = stop_event
            self._preview_producer_state = "starting"
            thread.start()
            self._preview_producer_state = "running"

    def _stop_monitor_producer(self) -> None:
        # Signal the monitor thread to stop and join it.
        with self._monitor_lock:
            ev = self._monitor_stop_event
            thr = self._monitor_thread
            # Null out first so concurrent starters see it
            self._monitor_stop_event = None
            self._monitor_thread = None
            self._preview_producer_state = "stopping"
        if ev is not None:
            ev.set()
        if thr is not None:
            thr.join(timeout=2.0)
        with self._monitor_lock:
            self._preview_producer_state = "idle"
            self._latest_frame_bytes = None

    def _monitor_loop(self, stop_event: threading.Event) -> None:
        """Producer loop that keeps _latest_frame_bytes populated.

        It prefers reading the scheduled latest image from disk (cheap) and only
        reads from the camera when no scheduled image is available. The loop
        respects _camera_lock when interacting with hardware.
        """
        last_activity = time.monotonic()
        try:
            while not stop_event.is_set():
                # Try scheduled image first
                image_path = self.latest_image()
                if image_path is not None:
                    try:
                        frame = image_path.read_bytes()
                    except Exception:
                        frame = None
                else:
                    frame = None

                if frame is None:
                    # No scheduled image on disk; attempt to capture one under camera lock
                    # Only do this if fake camera is not configured, otherwise skip.
                    if USE_FAKE_CAMERA:
                        # Nothing to do in fake-camera mode if no scheduled image
                        time.sleep(0.2)
                        continue
                    try:
                        with self._camera_lock:
                            # Prefer to reuse any controller-held camera (if set) else skip
                            if self._camera is not None:
                                # The real camera capture helper is intentionally
                                # thin here; we avoid configuring/starting cameras in
                                # the producer to reduce lifecycle complexity.
                                # If the controller exposes a capture helper, call it.
                                try:
                                    frame = self._camera.capture_preview_bytes()  # type: ignore[attr-defined]
                                except Exception:
                                    frame = None
                            else:
                                # No camera object available; skip capture attempt
                                frame = None
                    except Exception:
                        frame = None

                if frame is not None:
                    with self._monitor_lock:
                        self._latest_frame_bytes = frame
                    last_activity = time.monotonic()

                # If there are no subscribers, allow idle timeout to stop the producer
                with self._monitor_lock:
                    subs = self._preview_subscriber_count
                if subs == 0 and (time.monotonic() - last_activity) > self._monitor_idle_timeout:
                    break

                # Sleep a short time; producer doesn't need to be high-framerate here
                if stop_event.wait(0.4):
                    break
        finally:
            with self._monitor_lock:
                # clear state on exit
                self._monitor_thread = None
                self._monitor_stop_event = None
                self._preview_producer_state = "idle"

    def monitor_frames(self, ai_detection: bool = False) -> Generator[bytes, None, None]:
        """Explicit one-viewer stream from the producer's latest frame cache.

        The producer is single-instance: multiple consumers share the same cached
        latest frame. Consumers increment preview_subscriber_count and the first
        subscriber starts the producer.
        """
        if ai_detection:
            raise RuntimeError("AI monitor is removed from the active workflow.")
        # Reset any existing monitor stop event for this consumer
        self.stop_monitor()
        stop_event = threading.Event()
        with self._lock:
            self._monitor_stop_event = stop_event
            self._preview_subscriber_count += 1
            # ensure a single producer is running
            self._start_monitor_producer()
        try:
            while not stop_event.is_set():
                with self._monitor_lock:
                    frame = self._latest_frame_bytes
                if frame is not None:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                        + frame
                        + b"\r\n"
                    )
                # Wait briefly for the next update or stop
                if stop_event.wait(0.4):
                    break
        finally:
            with self._lock:
                # decrement subscribers and possibly stop producer when no subscribers
                self._preview_subscriber_count = max(0, self._preview_subscriber_count - 1)
                if self._preview_subscriber_count == 0:
                    # either stop immediately or let producer idle-timeout handle it
                    self._stop_monitor_producer()
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
        """Compatibility hook retained for app startup; active runtime has no events."""
        return None
