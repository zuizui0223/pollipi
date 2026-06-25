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
    MONITOR_SIZE,
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
        self._preview_producer_state = "idle"
        self._monitor_idle_timeout = 6.0  # seconds: idle timeout before stopping producer
        # Connection-level preview subscriber tracking. Each /mjpeg stream gets a
        # unique id and refreshes its last-seen timestamp while it is actively
        # iterated. A stream that stops being iterated (normal end, cancel, or an
        # unclean disconnect) stops refreshing and is reaped after
        # _subscriber_stale_after, so a stale subscriber can never hold the
        # producer running forever. We never trust a raw cumulative counter.
        self._subscriber_lock = threading.Lock()
        self._subscribers: dict[int, float] = {}  # subscriber_id -> last_seen (monotonic)
        self._subscriber_seq = 0
        self._subscriber_stale_after = 5.0  # seconds without a refresh => treated as gone

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
        self.probe_interval_sec: Optional[float] = None
        self.would_be_mode: str = "LOW"
        self.would_be_interval_sec: Optional[float] = None
        self.policy_profile_id = "three_stage_default_v1"
        self.simulation_run_id = "issue27-three-stage-baseline"
        self.kind = "three_stage"
        self.live_allowed = False
        self.live_adaptive_active = False

    def _build_status(self):
        from visit_monitor_server.api.schemas.capture import StatusResponse
        from visit_monitor_server.config import LIVE_ADAPTIVE_ENABLED
        from visit_monitor_server.services.policy_runtime import get_active_policy

        _policy_config, _policy_meta = get_active_policy()

        return StatusResponse(
            policy_name=_policy_meta.policy_name,
            policy_version=_policy_meta.policy_version,
            validation_status=_policy_meta.validation_status,
            probe_interval_sec=self.probe_interval_sec,
            would_be_mode=self.would_be_mode,
            would_be_interval_sec=self.would_be_interval_sec,
            live_adaptive_enabled=LIVE_ADAPTIVE_ENABLED,
            live_adaptive_active=self.live_adaptive_active,
            policy_profile_id=self.policy_profile_id,
            simulation_run_id=self.simulation_run_id,
            kind=self.kind,
            live_allowed=self.live_allowed,
            running=self.running,
            lifecycle_state=self.lifecycle_state,
            last_error=self.last_error,
            preview_subscriber_count=self._active_subscriber_count(),
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
        from pollipi_analysis.policy import get_policy_profile

        profile = get_policy_profile(request.policy_profile_id)
        with self._lock:
            if self.running or self._thread is not None:
                if profile.profile_id != self.policy_profile_id:
                    raise ValueError(
                        "policy_profile_id cannot be changed while capture is running."
                    )
                self.message = "Timelapse is already running; start was not duplicated."
                return self.status_unlocked()

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
            self.probe_interval_sec = None
            self.would_be_mode = "LOW"
            self.would_be_interval_sec = None
            self.policy_profile_id = profile.profile_id
            self.simulation_run_id = profile.simulation_run_id
            self.kind = profile.kind
            self.live_allowed = profile.live_allowed
            self.live_adaptive_active = False
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
            if "probe_interval_sec" in state:
                self.probe_interval_sec = state["probe_interval_sec"]
            if "would_be_mode" in state:
                self.would_be_mode = state["would_be_mode"]
            if "would_be_interval_sec" in state:
                self.would_be_interval_sec = state["would_be_interval_sec"]
            if "policy_profile_id" in state:
                self.policy_profile_id = state["policy_profile_id"]
            if "simulation_run_id" in state:
                self.simulation_run_id = state["simulation_run_id"]
            if "kind" in state:
                self.kind = state["kind"]
            if "live_allowed" in state:
                self.live_allowed = state["live_allowed"]
            if "live_adaptive_active" in state:
                self.live_adaptive_active = state["live_adaptive_active"]
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

    # --- connection-level preview subscriber tracking -------------------------
    def _register_subscriber(self) -> int:
        with self._subscriber_lock:
            self._subscriber_seq += 1
            sid = self._subscriber_seq
            self._subscribers[sid] = time.monotonic()
            return sid

    def _touch_subscriber(self, sid: int) -> None:
        with self._subscriber_lock:
            if sid in self._subscribers:
                self._subscribers[sid] = time.monotonic()

    def _remove_subscriber(self, sid: int) -> None:
        with self._subscriber_lock:
            self._subscribers.pop(sid, None)

    def _active_subscriber_count(self) -> int:
        """Number of live preview streams, after reaping stale ones.

        A subscriber that has not refreshed within _subscriber_stale_after is
        removed here, so a leaked/abandoned stream cannot keep the producer alive.
        """
        cutoff = time.monotonic() - self._subscriber_stale_after
        with self._subscriber_lock:
            for sid in [s for s, seen in self._subscribers.items() if seen < cutoff]:
                del self._subscribers[sid]
            return len(self._subscribers)

    def stop_monitor(self) -> None:
        with self._lock:
            event = self._monitor_stop_event
            if event is not None:
                event.set()
        # Also stop the dedicated monitor producer if any
        self._stop_monitor_producer()

    def _start_monitor_producer(self) -> None:
        # The preview producer must never run while scheduled capture is active.
        with self._lock:
            if self.running:
                return
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

    def _open_preview_camera(self):
        """Open a dedicated low-res camera for idle live preview.

        This is only called while the capture loop is not running, and hardware
        access is serialized by _camera_lock so scheduled capture still owns the
        sensor whenever timelapse is active.
        """
        if USE_FAKE_CAMERA:
            from visit_monitor_server.adapters.fake_camera import FakeCamera

            cam = FakeCamera()
            cam.configure(cam.create_preview_configuration(main={"size": MONITOR_SIZE}))
            cam.start()
            return cam

        from picamera2 import Picamera2  # type: ignore

        cam = Picamera2()
        cam.configure(cam.create_preview_configuration(main={"size": MONITOR_SIZE, "format": "RGB888"}))
        cam.start()
        return cam

    def _grab_preview_jpeg(self, cam) -> Optional[bytes]:
        try:
            if hasattr(cam, "capture_preview_bytes"):
                return cam.capture_preview_bytes()  # type: ignore[attr-defined]

            import io

            buffer = io.BytesIO()
            cam.capture_file(buffer, format="jpeg")
            return buffer.getvalue()
        except TypeError:
            try:
                self.image_dir.mkdir(parents=True, exist_ok=True)
                preview_path = self.image_dir / ".pollipi_preview_frame.jpg"
                cam.capture_file(str(preview_path))
                data = preview_path.read_bytes()
                preview_path.unlink(missing_ok=True)
                return data
            except Exception:
                return None
        except Exception:
            return None

    @staticmethod
    def _close_preview_camera(cam) -> None:
        try:
            cam.stop()
        except Exception:
            pass
        try:
            cam.close()
        except Exception:
            pass

    def _monitor_loop(self, stop_event: threading.Event) -> None:
        """Producer loop that keeps _latest_frame_bytes populated.

        While idle, open a dedicated low-res camera and stream live frames for
        framing. While capture is running, release that camera and only fall back
        to the latest scheduled image on disk.
        """
        last_activity = time.monotonic()
        preview_cam = None
        try:
            while not stop_event.is_set():
                with self._lock:
                    capture_running = self.running
                if capture_running:
                    # Scheduled capture owns the sensor; the preview producer must
                    # not run or linger during capture. Exit; the finally releases
                    # the preview camera. It will only restart once capture stops
                    # AND a live subscriber requests it.
                    break

                frame = None
                if preview_cam is None:
                    try:
                        with self._camera_lock:
                            preview_cam = self._open_preview_camera()
                        self._preview_producer_state = "running"
                    except Exception:
                        preview_cam = None
                if preview_cam is not None:
                    with self._camera_lock:
                        frame = self._grab_preview_jpeg(preview_cam)
                    if frame is None:
                        with self._camera_lock:
                            self._close_preview_camera(preview_cam)
                        preview_cam = None

                if frame is None:
                    image_path = self.latest_image()
                    if image_path is not None:
                        try:
                            frame = image_path.read_bytes()
                        except Exception:
                            frame = None

                if frame is not None:
                    with self._monitor_lock:
                        self._latest_frame_bytes = frame
                    last_activity = time.monotonic()

                # When no live subscriber remains (stale ones are reaped here),
                # allow the idle timeout to stop the producer.
                if (
                    self._active_subscriber_count() == 0
                    and (time.monotonic() - last_activity) > self._monitor_idle_timeout
                ):
                    break

                delay = 0.12 if preview_cam is not None else 0.4
                if stop_event.wait(delay):
                    break
        finally:
            if preview_cam is not None:
                with self._camera_lock:
                    self._close_preview_camera(preview_cam)
            with self._monitor_lock:
                # clear state on exit
                self._monitor_thread = None
                self._monitor_stop_event = None
                self._preview_producer_state = "idle"

    def monitor_frames(self, ai_detection: bool = False) -> Generator[bytes, None, None]:
        """Live preview stream from the shared producer's latest frame cache.

        Each stream registers a connection-level subscriber id and refreshes it
        while iterated; the producer is single-instance and shared. The stream is
        refused while scheduled capture is running, and ends if capture starts
        mid-stream, so the producer is never kept alive during capture.
        """
        if ai_detection:
            raise RuntimeError("AI monitor is removed from the active workflow.")
        # Never run a live preview stream while scheduled capture is active.
        with self._lock:
            if self.running:
                return

        sid = self._register_subscriber()
        # Ensure a single shared producer is running (no-op while capture runs).
        self._start_monitor_producer()
        try:
            while True:
                # Refresh liveness so this subscriber is not reaped as stale while
                # the client is actively consuming the stream.
                self._touch_subscriber(sid)
                with self._lock:
                    if self.running:
                        # Capture started mid-stream: end this preview stream so the
                        # producer is not kept alive during capture.
                        break
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
                # Brief pause before the next frame. On client disconnect the
                # generator's close() runs the finally below.
                time.sleep(0.4)
        finally:
            self._remove_subscriber(sid)
            # Stop the producer only when no live subscriber remains.
            if self._active_subscriber_count() == 0:
                self._stop_monitor_producer()

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
