"""TimelapseController – orchestrates camera lifecycle and the capture thread."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from visit_monitor_server.config import (
    AI_MONITOR_LABELS,
    AI_MONITOR_MODEL,
    AI_MONITOR_THRESHOLD,
    AUTONOMOUS_PATH,
    DEVICE_ID, DEVICE_NAME,
    CAMERA_LABEL, CAMERA_MODEL, CAMERA_PROFILE,
    IS_AI_CAMERA, IS_NOIR, IS_WIDE,
    MONITOR_SIZE,
    MONITOR_FRAME_INTERVAL_SEC,
    PREVIEW_PATH,
    USE_FAKE_CAMERA,
)


class TimelapseController:
    """Co-ordinates camera start/stop, capture threads, and preview streaming."""

    def __init__(self, image_dir: Path) -> None:
        self.image_dir = image_dir
        self._lock = threading.Lock()
        self._stop_event: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._camera = None
        self._camera_lock = threading.Lock()
        self._monitor_stop_event: Optional[threading.Event] = None
        self._monitor_closed_event: Optional[threading.Event] = None
        self._latest_preview_frame: Optional[bytes] = None
        self._latest_preview_time: Optional[float] = None

        # ---- Status fields ------------------------------------------------
        self.running = False
        self.interval_sec: Optional[float] = None
        self.capture_count = 0
        self.last_capture_time: Optional[str] = None
        self.last_image: Optional[str] = None
        self.message = "Stopped."
        self.auto_mode = False
        self.motion_trigger_mode = False
        self.hybrid_mode = False
        self.ml_assist_mode = False
        self.autonomous_mode = False
        self.adaptive_timelapse_mode = False
        self.motion_score: Optional[float] = None
        self.changed_area_ratio: Optional[float] = None
        self.mean_brightness: Optional[float] = None
        self.brightness_delta: Optional[float] = None
        self.wind_like_motion = False
        self.num_blobs = 0
        self.largest_blob_area = 0
        self.largest_blob_ratio: Optional[float] = None
        self.small_blob_count = 0
        self.motion_type = "none"
        self.insect_candidate = False
        self.detection_count = 0
        self.event_count = 0
        self.interval_reason = "Manual interval."
        self.site_id: Optional[str] = None
        self.flower_id: Optional[str] = None
        self.plant_species: Optional[str] = None
        self.observer: Optional[str] = None
        self.notes: Optional[str] = None
        self.comparison_session_id: Optional[str] = None
        self.camera_role: Optional[str] = None
        self.method_mode: Optional[str] = None
        self.roi_used = False
        self.roi_x: Optional[int] = None
        self.roi_y: Optional[int] = None
        self.roi_w: Optional[int] = None
        self.roi_h: Optional[int] = None
        self.roi_tracking = False
        self.roi_tracking_success = False
        self.roi_tracking_score: Optional[float] = None
        self.roi_search_margin = 30
        self.roi_tracking_min_score = 0.45
        self.initial_roi_x: Optional[int] = None
        self.initial_roi_y: Optional[int] = None
        self.initial_roi_w: Optional[int] = None
        self.initial_roi_h: Optional[int] = None
        self.tracked_roi_x: Optional[int] = None
        self.tracked_roi_y: Optional[int] = None
        self.tracked_roi_w: Optional[int] = None
        self.tracked_roi_h: Optional[int] = None
        self.roi_shift_x: Optional[int] = None
        self.roi_shift_y: Optional[int] = None

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _build_status(self):
        from visit_monitor_server.api.schemas.capture import StatusResponse

        return StatusResponse(
            running=self.running,
            interval_sec=self.interval_sec,
            capture_count=self.capture_count,
            last_capture_time=self.last_capture_time,
            last_image=self.last_image,
            message=self.message,
            auto_mode=self.auto_mode,
            motion_trigger_mode=self.motion_trigger_mode,
            hybrid_mode=self.hybrid_mode,
            ml_assist_mode=self.ml_assist_mode,
            autonomous_mode=self.autonomous_mode,
            adaptive_timelapse_mode=self.adaptive_timelapse_mode,
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
            roi_used=self.roi_used,
            roi_x=self.roi_x,
            roi_y=self.roi_y,
            roi_w=self.roi_w,
            roi_h=self.roi_h,
            roi_tracking=self.roi_tracking,
            roi_tracking_success=self.roi_tracking_success,
            roi_tracking_score=self.roi_tracking_score,
            roi_search_margin=self.roi_search_margin,
            roi_tracking_min_score=self.roi_tracking_min_score,
            initial_roi_x=self.initial_roi_x,
            initial_roi_y=self.initial_roi_y,
            initial_roi_w=self.initial_roi_w,
            initial_roi_h=self.initial_roi_h,
            tracked_roi_x=self.tracked_roi_x,
            tracked_roi_y=self.tracked_roi_y,
            tracked_roi_w=self.tracked_roi_w,
            tracked_roi_h=self.tracked_roi_h,
            roi_shift_x=self.roi_shift_x,
            roi_shift_y=self.roi_shift_y,
        )

    def status(self):
        with self._lock:
            return self._build_status()

    def status_unlocked(self):
        return self._build_status()

    # ------------------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------------------

    def start(self, request):
        self.stop()
        if request.autonomous_mode:
            self._save_autonomous_request(request)

        stop_event = threading.Event()
        with self._lock:
            self.running = True
            self.interval_sec = request.interval_sec
            self.capture_count = 0
            self.last_capture_time = None
            self.last_image = None
            self.message = "Starting timelapse."
            self.auto_mode = request.auto_mode or request.motion_trigger_mode or request.hybrid_mode
            self.motion_trigger_mode = request.motion_trigger_mode
            self.hybrid_mode = request.hybrid_mode
            self.ml_assist_mode = request.ml_assist_mode
            self.autonomous_mode = request.autonomous_mode
            self.adaptive_timelapse_mode = request.adaptive_timelapse_mode
            self.motion_score = None
            self.changed_area_ratio = None
            self.mean_brightness = None
            self.brightness_delta = None
            self.wind_like_motion = False
            self.num_blobs = 0
            self.largest_blob_area = 0
            self.largest_blob_ratio = None
            self.small_blob_count = 0
            self.motion_type = "none"
            self.insect_candidate = False
            self.detection_count = 0
            self.event_count = 0
            self.site_id = request.site_id
            self.flower_id = request.flower_id
            self.plant_species = request.plant_species
            self.observer = request.observer
            self.notes = request.notes
            self.comparison_session_id = request.comparison_session_id
            self.camera_role = request.camera_role
            self.method_mode = request.method_mode
            _roi = self._roi_tuple(request)
            self.roi_used = _roi is not None
            self.roi_x = request.roi_x
            self.roi_y = request.roi_y
            self.roi_w = request.roi_w
            self.roi_h = request.roi_h
            self.roi_tracking = bool(request.roi_tracking and self.roi_used)
            self.roi_tracking_success = False
            self.roi_tracking_score = None
            self.roi_search_margin = request.roi_search_margin
            self.roi_tracking_min_score = request.roi_tracking_min_score
            self.initial_roi_x = request.roi_x if self.roi_tracking else None
            self.initial_roi_y = request.roi_y if self.roi_tracking else None
            self.initial_roi_w = request.roi_w if self.roi_tracking else None
            self.initial_roi_h = request.roi_h if self.roi_tracking else None
            self.tracked_roi_x = request.roi_x if self.roi_tracking else None
            self.tracked_roi_y = request.roi_y if self.roi_tracking else None
            self.tracked_roi_w = request.roi_w if self.roi_tracking else None
            self.tracked_roi_h = request.roi_h if self.roi_tracking else None
            self.roi_shift_x = 0 if self.roi_tracking else None
            self.roi_shift_y = 0 if self.roi_tracking else None
            if request.adaptive_timelapse_mode:
                self.interval_reason = "Waiting for adaptive baseline."
            elif request.hybrid_mode:
                self.interval_reason = "Waiting for scheduled and motion baselines."
            elif request.motion_trigger_mode:
                self.interval_reason = "Waiting for motion-trigger baseline."
            else:
                self.interval_reason = (
                    "Waiting for background baseline." if request.auto_mode else "Manual interval."
                )
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
            was_active = self.running or thread is not None
            if stop_event is not None:
                stop_event.set()

        if thread is not None and thread is not threading.current_thread():
            thread.join()

        with self._lock:
            self.running = False
            self._stop_event = None
            self._thread = None
            if not preserve_autonomous:
                self.autonomous_mode = False
            if was_active:
                self.message = "Timelapse stopped."
            status = self.status_unlocked()
        if not preserve_autonomous:
            self._clear_autonomous_request()
        return status

    # ------------------------------------------------------------------
    # Capture thread
    # ------------------------------------------------------------------

    def _run_loop(self, stop_event: threading.Event, request) -> None:
        from visit_monitor_server.services import get_trainer
        from visit_monitor_server.services.capture_loop import run_capture_loop

        run_capture_loop(
            stop_event=stop_event,
            request=request,
            image_dir=self.image_dir,
            camera_lock=self._camera_lock,
            set_camera=self._set_camera,
            update_state=self._apply_state_update,
            set_message=lambda m: self._set_message_locked(m),
            trainer=get_trainer(),
        )

    def _set_camera(self, camera) -> None:
        with self._lock:
            self._camera = camera
            if camera is None:
                self.running = False

    def _set_message_locked(self, msg: str) -> None:
        with self._lock:
            self.message = msg

    def _apply_state_update(self, state: dict) -> None:
        with self._lock:
            if "interval_sec" in state:
                self.interval_sec = state["interval_sec"]
            if "message" in state:
                self.message = state["message"]
            if "motion_score" in state:
                self.motion_score = state["motion_score"]
            if "metrics" in state and state["metrics"] is not None:
                self._update_motion_metrics_unlocked(state["metrics"])
            elif "metrics" in state and state["metrics"] is None:
                self._clear_motion_metrics_unlocked()
            if "insect_candidate" in state:
                self.insect_candidate = state["insect_candidate"]
            if "interval_reason" in state:
                self.interval_reason = state["interval_reason"]
            self.capture_count += state.get("capture_count_delta", 0)
            self.detection_count += state.get("detection_count_delta", 0)
            self.event_count += state.get("event_count_delta", 0)
            if state.get("last_capture_time") is not None:
                self.last_capture_time = state["last_capture_time"]
            if state.get("last_image") is not None:
                self.last_image = state["last_image"]

    # ------------------------------------------------------------------
    # Preview / monitor
    # ------------------------------------------------------------------

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
        with self._lock:
            camera = self._camera
            monitor_active = self._monitor_stop_event is not None
            cached_frame = self._latest_preview_frame

        if camera is not None:
            with self._camera_lock:
                try:
                    camera.capture_file(str(PREVIEW_PATH))
                except Exception:
                    camera.capture_file(str(PREVIEW_PATH), name="lores")
                frame = PREVIEW_PATH.read_bytes()
                self._cache_preview_frame(frame)
                return frame

        if cached_frame:
            return cached_frame

        if monitor_active:
            frame = self._wait_for_cached_preview(timeout=2.0)
            if frame:
                return frame
            raise RuntimeError("Monitor is starting; preview frame is not ready yet.")

        if USE_FAKE_CAMERA:
            from visit_monitor_server.adapters.fake_camera import FakeCamera
            fc = FakeCamera()
            fc.start()
            fc.capture_file(str(PREVIEW_PATH))
            fc.stop()
            fc.close()
            frame = PREVIEW_PATH.read_bytes()
            self._cache_preview_frame(frame)
            return frame

        from picamera2 import Picamera2  # type: ignore

        with self._camera_lock:
            preview_camera = Picamera2()
            try:
                preview_camera.configure(
                    preview_camera.create_preview_configuration(main={"size": (1280, 720)})
                )
                preview_camera.start()
                time.sleep(1)
                preview_camera.capture_file(str(PREVIEW_PATH))
                frame = PREVIEW_PATH.read_bytes()
                self._cache_preview_frame(frame)
                return frame
            finally:
                try:
                    preview_camera.stop()
                finally:
                    preview_camera.close()

    def _cache_preview_frame(self, frame: bytes) -> None:
        if not frame:
            return
        with self._lock:
            self._latest_preview_frame = frame
            self._latest_preview_time = time.monotonic()

    def _wait_for_cached_preview(self, timeout: float) -> Optional[bytes]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                frame = self._latest_preview_frame
            if frame:
                return frame
            time.sleep(0.05)
        return None

    def stop_monitor(self) -> None:
        with self._lock:
            stop_event = self._monitor_stop_event
            closed_event = self._monitor_closed_event
            if stop_event is not None:
                stop_event.set()
        if closed_event is not None:
            closed_event.wait(timeout=5)

    def monitor_frames(self, ai_detection: bool = False) -> Generator[bytes, None, None]:
        self.stop_monitor()
        stop_event = threading.Event()
        closed_event = threading.Event()
        temporary_camera = None
        imx500 = None
        intrinsics = None
        with self._lock:
            self._monitor_stop_event = stop_event
            self._monitor_closed_event = closed_event
            timelapse_camera = self._camera

        try:
            if ai_detection and timelapse_camera is not None:
                return
            if timelapse_camera is None:
                if USE_FAKE_CAMERA:
                    from visit_monitor_server.adapters.fake_camera import FakeCamera
                    temporary_camera = FakeCamera()
                    temporary_camera.configure(
                        temporary_camera.create_preview_configuration(main={"size": MONITOR_SIZE})
                    )
                    temporary_camera.start()
                else:
                    from picamera2 import Picamera2  # type: ignore
                    with self._camera_lock:
                        if ai_detection:
                            from visit_monitor_server.adapters.imx500 import load_imx500
                            imx500, intrinsics = load_imx500(AI_MONITOR_MODEL)
                            temporary_camera = Picamera2(imx500.camera_num)
                            temporary_camera.configure(
                                temporary_camera.create_preview_configuration(
                                    main={"size": MONITOR_SIZE, "format": "RGB888"},
                                    controls={"FrameRate": intrinsics.inference_rate},
                                    buffer_count=12,
                                )
                            )
                            imx500.show_network_fw_progress_bar()
                        else:
                            temporary_camera = Picamera2()
                            temporary_camera.configure(
                                temporary_camera.create_preview_configuration(
                                    main={"size": MONITOR_SIZE}
                                )
                            )
                        temporary_camera.start()
                if stop_event.wait(0.5):
                    return

            while not stop_event.is_set():
                with self._lock:
                    active_camera = self._camera
                camera = active_camera or temporary_camera
                if camera is None:
                    break
                with self._camera_lock:
                    if ai_detection and temporary_camera is not None and imx500 is not None:
                        frame = self._ai_detection_frame(temporary_camera, imx500, intrinsics)
                    elif active_camera is not None:
                        camera.capture_file(str(PREVIEW_PATH), name="lores")
                        frame = PREVIEW_PATH.read_bytes()
                    else:
                        camera.capture_file(str(PREVIEW_PATH))
                        frame = PREVIEW_PATH.read_bytes()
                self._cache_preview_frame(frame)
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                    + frame
                    + b"\r\n"
                )
                if stop_event.wait(MONITOR_FRAME_INTERVAL_SEC):
                    break
        finally:
            if temporary_camera is not None:
                with self._camera_lock:
                    try:
                        temporary_camera.stop()
                    finally:
                        temporary_camera.close()
            with self._lock:
                if self._monitor_stop_event is stop_event:
                    self._monitor_stop_event = None
                    self._monitor_closed_event = None
            closed_event.set()

    @staticmethod
    def _ai_detection_frame(camera, imx500, intrinsics) -> bytes:
        from visit_monitor_server.adapters.imx500 import render_detections

        request = camera.capture_request()
        try:
            metadata = request.get_metadata()
            image = request.make_array("main")
            outputs = imx500.get_outputs(metadata, add_batch=True)
            return render_detections(
                image, outputs, imx500, intrinsics, metadata,
                AI_MONITOR_THRESHOLD, AI_MONITOR_LABELS,
            )
        finally:
            request.release()

    # ------------------------------------------------------------------
    # Motion metrics helpers
    # ------------------------------------------------------------------

    def _update_motion_metrics_unlocked(self, metrics: dict) -> None:
        self.motion_score = metrics.get("motion_score")
        self.changed_area_ratio = metrics.get("changed_area_ratio")
        self.mean_brightness = metrics.get("mean_brightness")
        self.brightness_delta = metrics.get("brightness_delta")
        self.wind_like_motion = bool(metrics.get("wind_like_motion"))
        self.num_blobs = int(metrics.get("num_blobs") or 0)
        self.largest_blob_area = int(metrics.get("largest_blob_area") or 0)
        self.largest_blob_ratio = metrics.get("largest_blob_ratio")
        self.small_blob_count = int(metrics.get("small_blob_count") or 0)
        self.motion_type = str(metrics.get("motion_type") or "none")
        self.roi_used = bool(metrics.get("roi_used"))
        self.roi_x = metrics.get("roi_x")
        self.roi_y = metrics.get("roi_y")
        self.roi_w = metrics.get("roi_w")
        self.roi_h = metrics.get("roi_h")
        self.roi_tracking = bool(metrics.get("roi_tracking"))
        self.roi_tracking_success = bool(metrics.get("roi_tracking_success"))
        self.roi_tracking_score = metrics.get("roi_tracking_score")
        self.roi_search_margin = int(metrics.get("roi_search_margin") or self.roi_search_margin)
        self.roi_tracking_min_score = float(
            metrics.get("roi_tracking_min_score") or self.roi_tracking_min_score
        )
        self.initial_roi_x = metrics.get("initial_roi_x")
        self.initial_roi_y = metrics.get("initial_roi_y")
        self.initial_roi_w = metrics.get("initial_roi_w")
        self.initial_roi_h = metrics.get("initial_roi_h")
        self.tracked_roi_x = metrics.get("tracked_roi_x")
        self.tracked_roi_y = metrics.get("tracked_roi_y")
        self.tracked_roi_w = metrics.get("tracked_roi_w")
        self.tracked_roi_h = metrics.get("tracked_roi_h")
        self.roi_shift_x = metrics.get("roi_shift_x")
        self.roi_shift_y = metrics.get("roi_shift_y")

    def _clear_motion_metrics_unlocked(self) -> None:
        self.motion_score = None
        self.changed_area_ratio = None
        self.mean_brightness = None
        self.brightness_delta = None
        self.wind_like_motion = False
        self.num_blobs = 0
        self.largest_blob_area = 0
        self.largest_blob_ratio = None
        self.small_blob_count = 0
        self.motion_type = "none"
        self.roi_tracking_success = False
        self.roi_tracking_score = None

    # ------------------------------------------------------------------
    # Label helpers (delegated to image_store)
    # ------------------------------------------------------------------

    def _label_index(self):
        from visit_monitor_server.services.image_store import label_index
        return label_index()

    def _review_status(self, source):
        from visit_monitor_server.services.image_store import review_status
        return review_status(source)

    def _register_label(self, image_path, label, source):
        from visit_monitor_server.services.image_store import register_label
        register_label(image_path, label, source)

    def _remove_label(self, filename: str) -> None:
        from visit_monitor_server.services.image_store import remove_label
        remove_label(filename)

    def migrate_legacy_candidates(self) -> None:
        from visit_monitor_server.config import IMAGE_DIR, LEGACY_CANDIDATE_DIR
        from visit_monitor_server.services.image_store import register_label

        if not LEGACY_CANDIDATE_DIR.is_dir():
            return
        for candidate_path in LEGACY_CANDIDATE_DIR.iterdir():
            original_path = IMAGE_DIR / candidate_path.name
            if candidate_path.suffix.lower() in {".jpg", ".jpeg"} and original_path.is_file():
                register_label(original_path, "positive", "legacy_motion_candidate")

    # ------------------------------------------------------------------
    # Autonomous session helpers
    # ------------------------------------------------------------------

    def _save_autonomous_request(self, request) -> None:
        from visit_monitor_server.api.schemas.capture import StartRequest  # noqa: F401

        AUTONOMOUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(request, "model_dump_json"):
            payload = request.model_dump_json(indent=2)
        else:
            payload = request.json(indent=2)
        AUTONOMOUS_PATH.write_text(payload, encoding="utf-8")

    @staticmethod
    def _clear_autonomous_request() -> None:
        if AUTONOMOUS_PATH.exists():
            AUTONOMOUS_PATH.unlink()

    def resume_autonomous(self) -> None:
        if not AUTONOMOUS_PATH.is_file():
            return
        try:
            from visit_monitor_server.api.schemas.capture import StartRequest

            payload = json.loads(AUTONOMOUS_PATH.read_text(encoding="utf-8"))
            if hasattr(StartRequest, "model_validate"):
                request = StartRequest.model_validate(payload)
            else:
                request = StartRequest.parse_obj(payload)
            if request.autonomous_mode:
                self.start(request)
        except Exception as exc:
            with self._lock:
                self.message = f"Autonomous resume error: {exc}"

    # ------------------------------------------------------------------
    # Private utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _roi_tuple(request) -> Optional[tuple[int, int, int, int]]:
        if None in (request.roi_x, request.roi_y, request.roi_w, request.roi_h):
            return None
        return (int(request.roi_x), int(request.roi_y), int(request.roi_w), int(request.roi_h))
