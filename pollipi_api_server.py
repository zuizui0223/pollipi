"""PolliPi timelapse control API for Raspberry Pi Camera Module 3."""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask


IMAGE_DIR = Path(
    os.getenv("POLLIPI_IMAGE_DIR", str(Path.home() / "pollipi_timelapse" / "images"))
).expanduser()
METRICS_PATH = IMAGE_DIR / "adaptive_metrics.csv"
OBSERVATION_LOG_PATH = IMAGE_DIR / "observation_events.csv"
EVENT_LOG_PATH = IMAGE_DIR / "event_log.csv"
LABEL_LOG_PATH = IMAGE_DIR / "image_labels.csv"
POSITIVE_DIR = IMAGE_DIR / "positive"
NEGATIVE_DIR = IMAGE_DIR / "negative"
LEGACY_CANDIDATE_DIR = IMAGE_DIR / "candidates"
MODEL_DIR = IMAGE_DIR.parent / "models"
MODEL_PATH = MODEL_DIR / "insect_presence_svm.xml"
MODEL_INFO_PATH = MODEL_DIR / "insect_presence_model.json"
FLOWER_ROI_MODEL = os.getenv("POLLIPI_FLOWER_ROI_MODEL", "")
AUTONOMOUS_PATH = IMAGE_DIR.parent / "autonomous_run.json"
WEB_DIR = Path(__file__).parent / "web"
PREVIEW_PATH = Path("/tmp/pollipi_preview.jpg")
MONITOR_SIZE = (640, 360)
MONITOR_FRAME_INTERVAL_SEC = 0.25
AI_MONITOR_MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
AI_MONITOR_THRESHOLD = 0.55
AI_MONITOR_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "-", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "-", "backpack",
    "umbrella", "-", "-", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "-", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
    "donut", "cake", "chair", "couch", "potted plant", "bed", "-", "dining table", "-",
    "-", "toilet", "-", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "-", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


DEVICE_ID = os.getenv("POLLIPI_DEVICE_ID", socket.gethostname())
DEVICE_NAME = os.getenv("POLLIPI_DEVICE_NAME", socket.gethostname())
CAMERA_LABEL = os.getenv("POLLIPI_CAMERA_LABEL", "PolliPi Camera")
CAMERA_MODEL = os.getenv("POLLIPI_CAMERA_MODEL", "Picamera2 camera")
CAMERA_PROFILE = os.getenv("POLLIPI_CAMERA_PROFILE", "unspecified")
IS_AI_CAMERA = env_bool("POLLIPI_IS_AI_CAMERA")
IS_NOIR = env_bool("POLLIPI_IS_NOIR")
IS_WIDE = env_bool("POLLIPI_IS_WIDE")
FALSE_POSITIVE_REASONS = {
    "",
    "wind",
    "shadow",
    "flower_movement",
    "camera_shake",
    "non_insect_object",
    "lighting_change",
    "unclear",
    "other",
}
EVENT_LOG_COLUMNS = [
    "event_id", "timestamp", "image_filename",
    "device_id", "device_name", "camera_label", "camera_model", "camera_profile",
    "is_ai_camera", "is_noir", "is_wide",
    "site_id", "flower_id", "plant_species", "observer", "notes",
    "comparison_session_id", "camera_role", "method_mode",
    "motion_score", "changed_area_ratio", "mean_brightness", "brightness_delta",
    "wind_like_motion", "num_blobs", "largest_blob_area", "largest_blob_ratio",
    "small_blob_count", "motion_type", "roi_used", "roi_x", "roi_y", "roi_w", "roi_h",
    "roi_tracking", "roi_tracking_success", "roi_tracking_score", "roi_search_margin",
    "roi_tracking_min_score", "initial_roi_x", "initial_roi_y", "initial_roi_w", "initial_roi_h",
    "tracked_roi_x", "tracked_roi_y", "tracked_roi_w", "tracked_roi_h", "roi_shift_x", "roi_shift_y",
    "manual_label", "manual_taxon", "false_positive_reason", "manual_notes", "reviewed_at",
]


class StartRequest(BaseModel):
    interval_sec: float = Field(..., ge=1, le=3600)
    site_id: Optional[str] = None
    flower_id: Optional[str] = None
    plant_species: Optional[str] = None
    observer: Optional[str] = None
    notes: Optional[str] = None
    comparison_session_id: Optional[str] = None
    camera_role: Optional[str] = None
    method_mode: Optional[str] = None
    roi_x: Optional[int] = None
    roi_y: Optional[int] = None
    roi_w: Optional[int] = None
    roi_h: Optional[int] = None
    roi_tracking: bool = False
    roi_search_margin: int = Field(default=30, ge=0, le=160)
    roi_tracking_min_score: float = Field(default=0.45, ge=-1.0, le=1.0)
    auto_mode: bool = False
    motion_trigger_mode: bool = False
    hybrid_mode: bool = False
    ml_assist_mode: bool = False
    autonomous_mode: bool = False
    idle_interval_sec: float = Field(default=60, ge=1, le=3600)
    detection_interval_sec: float = Field(default=3, ge=1, le=3600)
    pixel_difference: int = Field(default=30, ge=1, le=255)
    motion_ratio: float = Field(default=0.01, ge=0.0001, le=1)


class StatusResponse(BaseModel):
    running: bool
    interval_sec: Optional[float]
    capture_count: int
    last_capture_time: Optional[str]
    last_image: Optional[str]
    message: str
    auto_mode: bool
    motion_trigger_mode: bool
    hybrid_mode: bool
    ml_assist_mode: bool
    autonomous_mode: bool
    motion_score: Optional[float]
    changed_area_ratio: Optional[float]
    mean_brightness: Optional[float]
    brightness_delta: Optional[float]
    wind_like_motion: bool
    num_blobs: int
    largest_blob_area: int
    largest_blob_ratio: Optional[float]
    small_blob_count: int
    motion_type: str
    insect_candidate: bool
    detection_count: int
    event_count: int
    interval_reason: str
    device_id: str
    device_name: str
    camera_label: str
    camera_model: str
    camera_profile: str
    is_ai_camera: bool
    is_noir: bool
    is_wide: bool
    site_id: Optional[str]
    flower_id: Optional[str]
    plant_species: Optional[str]
    observer: Optional[str]
    notes: Optional[str]
    comparison_session_id: Optional[str]
    camera_role: Optional[str]
    method_mode: Optional[str]
    roi_used: bool
    roi_x: Optional[int]
    roi_y: Optional[int]
    roi_w: Optional[int]
    roi_h: Optional[int]
    roi_tracking: bool
    roi_tracking_success: bool
    roi_tracking_score: Optional[float]
    roi_search_margin: int
    roi_tracking_min_score: float
    initial_roi_x: Optional[int]
    initial_roi_y: Optional[int]
    initial_roi_w: Optional[int]
    initial_roi_h: Optional[int]
    tracked_roi_x: Optional[int]
    tracked_roi_y: Optional[int]
    tracked_roi_w: Optional[int]
    tracked_roi_h: Optional[int]
    roi_shift_x: Optional[int]
    roi_shift_y: Optional[int]


class DeviceInfoResponse(BaseModel):
    device_id: str
    device_name: str
    camera_label: str
    camera_model: str
    camera_profile: str
    is_ai_camera: bool
    is_noir: bool
    is_wide: bool
    app_name: str = "PolliPi Field Observer"
    api_version: str = "1"


class SystemInfoResponse(BaseModel):
    storage_path: str
    storage_total_bytes: int
    storage_used_bytes: int
    storage_free_bytes: int
    storage_percent_used: float
    battery_percent: Optional[float] = None
    undervoltage_now: Optional[bool]
    undervoltage_occurred: Optional[bool]
    throttled_raw: Optional[str]
    power_message: str


class ImageInfo(BaseModel):
    filename: str
    captured_at: str
    size_bytes: int
    url: str
    label: Optional[str] = None
    label_source: Optional[str] = None
    review_status: str = "unlabeled"


class ImageListResponse(BaseModel):
    image_dir: str
    collection: str
    image_count: int
    total_size_bytes: int
    images: list[ImageInfo]


class DeleteImageResponse(BaseModel):
    deleted: str
    message: str


class DeleteAllRequest(BaseModel):
    confirm: str


class DeleteAllResponse(BaseModel):
    deleted_count: int
    message: str


class LabelRequest(BaseModel):
    label: str


class LabelResponse(BaseModel):
    filename: str
    label: str
    label_source: str
    review_status: str
    message: str


class EventListResponse(BaseModel):
    event_count: int
    events: list[dict[str, str]]


class EventLabelRequest(BaseModel):
    manual_label: Optional[str] = None
    manual_taxon: Optional[str] = None
    false_positive_reason: Optional[str] = None
    manual_notes: Optional[str] = None


class EventLabelResponse(BaseModel):
    event_id: str
    manual_label: str
    manual_taxon: str
    false_positive_reason: str
    manual_notes: str
    reviewed_at: str
    message: str


class TrainingStatusResponse(BaseModel):
    running: bool
    positive_count: int
    negative_count: int
    auto_labeled_count: int
    reviewed_count: int
    model_available: bool
    trained_at: Optional[str]
    validation_accuracy: Optional[float]
    message: str


class RoiSuggestionResponse(BaseModel):
    available: bool
    suggested: bool
    roi_x: Optional[int] = None
    roi_y: Optional[int] = None
    roi_w: Optional[int] = None
    roi_h: Optional[int] = None
    model_path: Optional[str] = None
    message: str


class TimelapseController:
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

    def status(self) -> StatusResponse:
        with self._lock:
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

    def start(self, request: StartRequest) -> StatusResponse:
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
            self.roi_used = self._roi_tuple(request) is not None
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
            if request.hybrid_mode:
                self.interval_reason = "Waiting for scheduled and motion baselines."
            elif request.motion_trigger_mode:
                self.interval_reason = "Waiting for motion-trigger baseline."
            else:
                self.interval_reason = "Waiting for background baseline." if request.auto_mode else "Manual interval."
            self._stop_event = stop_event
            self._thread = threading.Thread(
                target=self._capture_loop,
                args=(stop_event, request),
                name="pollipi-timelapse",
                daemon=True,
            )
            thread = self._thread

        thread.start()
        return self.status()

    def stop(self, preserve_autonomous: bool = False) -> StatusResponse:
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

    def status_unlocked(self) -> StatusResponse:
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

        from picamera2 import Picamera2

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
                from picamera2 import Picamera2

                with self._camera_lock:
                    if ai_detection:
                        from picamera2.devices import IMX500
                        from picamera2.devices.imx500 import NetworkIntrinsics

                        imx500 = IMX500(AI_MONITOR_MODEL)
                        intrinsics = imx500.network_intrinsics or NetworkIntrinsics()
                        intrinsics.task = "object detection"
                        intrinsics.update_with_defaults()
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
                            temporary_camera.create_preview_configuration(main={"size": MONITOR_SIZE})
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
                    if ai_detection and temporary_camera is not None:
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
        import cv2

        request = camera.capture_request()
        try:
            metadata = request.get_metadata()
            image = request.make_array("main")
            outputs = imx500.get_outputs(metadata, add_batch=True)
            if outputs is not None:
                _, input_height = imx500.get_input_size()
                boxes, scores, classes = outputs[0][0], outputs[1][0], outputs[2][0]
                if intrinsics.bbox_normalization:
                    boxes = boxes / input_height
                if intrinsics.bbox_order == "xy":
                    boxes = boxes[:, [1, 0, 3, 2]]
                labels = list(intrinsics.labels or AI_MONITOR_LABELS)
                for box, score, category in zip(boxes, scores, classes):
                    if float(score) <= AI_MONITOR_THRESHOLD:
                        continue
                    x, y, width, height = imx500.convert_inference_coords(box, metadata, camera)
                    category_number = int(category)
                    label = labels[category_number] if category_number < len(labels) else f"class_{category_number}"
                    caption = f"{label} {float(score):.2f}"
                    cv2.rectangle(image, (x, y), (x + width, y + height), (0, 255, 0), 2)
                    cv2.putText(
                        image,
                        caption,
                        (x + 3, max(y + 16, 16)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (0, 0, 255),
                        1,
                    )
            encoded, buffer = cv2.imencode(".jpg", image)
            if not encoded:
                raise RuntimeError("AI monitor JPEG encoding failed.")
            return buffer.tobytes()
        finally:
            request.release()

    def _capture_loop(self, stop_event: threading.Event, request: StartRequest) -> None:
        camera = None
        background = None
        try:
            from picamera2 import Picamera2

            self.image_dir.mkdir(parents=True, exist_ok=True)
            with self._camera_lock:
                camera = Picamera2()
                camera.configure(
                    camera.create_still_configuration(lores={"size": MONITOR_SIZE, "format": "YUV420"})
                )
                camera.start()
            with self._lock:
                self._camera = camera
            roi = self._roi_tuple(request)
            roi_tracker = self._new_roi_tracker(request, roi)

            # Give automatic exposure and white balance a moment to settle.
            if stop_event.wait(2):
                return

            with self._lock:
                self.message = "Timelapse running."

            next_scheduled_time = time.monotonic()
            while not stop_event.is_set():
                captured_at = datetime.now().astimezone()
                if request.hybrid_mode:
                    with self._camera_lock:
                        frame = camera.capture_array("lores")
                    metrics, insect_candidate, background = self._detect_motion_with_tracking(
                        frame,
                        background,
                        request.pixel_difference,
                        request.motion_ratio,
                        roi,
                        roi_tracker,
                        request,
                    )
                    score = metrics["motion_score"]
                    check_time = time.monotonic()
                    scheduled_due = check_time >= next_scheduled_time
                    image_path = None
                    capture_type = "none"
                    if scheduled_due:
                        capture_type = "scheduled_event" if insect_candidate else "scheduled"
                        filename = captured_at.strftime(f"{capture_type}_%Y%m%d_%H%M%S_%f.jpg")
                        image_path = self.image_dir / filename
                        with self._camera_lock:
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
                        image_path = self.image_dir / filename
                        with self._camera_lock:
                            camera.capture_file(str(image_path))
                        interval_reason = "Motion candidate detected; supplemental event image saved."
                    elif score is None:
                        interval_reason = "Motion baseline captured; scheduled observation continues."
                    else:
                        interval_reason = "No motion candidate; waiting for next scheduled image."
                    self._write_observation_event(
                        captured_at,
                        image_path,
                        capture_type,
                        request.interval_sec,
                        request.detection_interval_sec,
                        score,
                        metrics,
                        insect_candidate,
                        interval_reason,
                        request,
                    )
                    if insect_candidate:
                        self._write_event_log(captured_at, image_path, metrics, request)
                    if image_path is not None:
                        self._label_captured_image(
                            image_path,
                            "positive" if insect_candidate else "negative",
                            request.ml_assist_mode,
                        )
                    with self._lock:
                        self.interval_sec = request.interval_sec
                        self.message = "Research hybrid observation running."
                        self.motion_score = score
                        self._update_motion_metrics_unlocked(metrics)
                        self.insect_candidate = insect_candidate
                        self.interval_reason = interval_reason
                        if insect_candidate:
                            self.detection_count += 1
                            self.event_count += 1
                        if image_path is not None:
                            self.capture_count += 1
                            self.last_capture_time = captured_at.isoformat(timespec="seconds")
                            self.last_image = str(image_path)
                    if stop_event.wait(request.detection_interval_sec):
                        break
                    continue

                if request.motion_trigger_mode:
                    with self._camera_lock:
                        frame = camera.capture_array("lores")
                    metrics, insect_candidate, background = self._detect_motion_with_tracking(
                        frame,
                        background,
                        request.pixel_difference,
                        request.motion_ratio,
                        roi,
                        roi_tracker,
                        request,
                    )
                    score = metrics["motion_score"]
                    image_path = None
                    if score is None:
                        interval_reason = "Motion-trigger baseline captured; waiting for change."
                    elif insect_candidate:
                        filename = captured_at.strftime("motion_%Y%m%d_%H%M%S_%f.jpg")
                        image_path = self.image_dir / filename
                        with self._camera_lock:
                            camera.capture_file(str(image_path))
                        interval_reason = "Motion candidate detected; image saved."
                    else:
                        interval_reason = "Monitoring motion; no image saved."
                    self._write_metric(
                        captured_at,
                        image_path,
                        request.detection_interval_sec,
                        score,
                        metrics,
                        insect_candidate,
                        interval_reason,
                        request,
                    )
                    if insect_candidate:
                        self._write_event_log(captured_at, image_path, metrics, request)
                    if image_path is not None:
                        self._label_captured_image(image_path, "positive", request.ml_assist_mode)
                    with self._lock:
                        self.interval_sec = request.detection_interval_sec
                        self.message = "Motion-trigger observation running."
                        self.motion_score = score
                        self._update_motion_metrics_unlocked(metrics)
                        self.insect_candidate = insect_candidate
                        self.interval_reason = interval_reason
                        if image_path is not None:
                            self.capture_count += 1
                            self.detection_count += 1
                            self.event_count += 1
                            self.last_capture_time = captured_at.isoformat(timespec="seconds")
                            self.last_image = str(image_path)
                    if stop_event.wait(request.detection_interval_sec):
                        break
                    continue

                filename = captured_at.strftime("image_%Y%m%d_%H%M%S_%f.jpg")
                image_path = self.image_dir / filename
                with self._camera_lock:
                    camera.capture_file(str(image_path))

                next_interval = request.interval_sec
                score = None
                insect_candidate = False
                interval_reason = "Manual interval."
                if request.auto_mode:
                    with self._camera_lock:
                        frame = camera.capture_array("lores")
                    metrics, insect_candidate, background = self._detect_motion_with_tracking(
                        frame,
                        background,
                        request.pixel_difference,
                        request.motion_ratio,
                        roi,
                        roi_tracker,
                        request,
                    )
                    score = metrics["motion_score"]
                    if score is None:
                        next_interval = request.idle_interval_sec
                        interval_reason = "Background baseline captured."
                    elif insect_candidate:
                        next_interval = request.detection_interval_sec
                        interval_reason = "Motion candidate detected."
                    else:
                        next_interval = request.idle_interval_sec
                        interval_reason = "No motion candidate; power-saving interval."
                    self._write_metric(
                        captured_at,
                        image_path,
                        next_interval,
                        score,
                        metrics,
                        insect_candidate,
                        interval_reason,
                        request,
                    )
                    if insect_candidate:
                        self._write_event_log(captured_at, image_path, metrics, request)
                    self._label_captured_image(
                        image_path,
                        "positive" if insect_candidate else "negative",
                        request.ml_assist_mode,
                    )
                elif request.ml_assist_mode and MODEL_PATH.is_file():
                    self._label_captured_image(image_path, "negative", True)

                with self._lock:
                    self.capture_count += 1
                    self.interval_sec = next_interval
                    self.last_capture_time = captured_at.isoformat(timespec="seconds")
                    self.last_image = str(image_path)
                    self.message = "Timelapse running."
                    self.motion_score = score
                    if request.auto_mode:
                        self._update_motion_metrics_unlocked(metrics)
                    else:
                        self._clear_motion_metrics_unlocked()
                    self.insect_candidate = insect_candidate
                    if insect_candidate:
                        self.detection_count += 1
                        self.event_count += 1
                    self.interval_reason = interval_reason

                if stop_event.wait(next_interval):
                    break
        except Exception as exc:
            with self._lock:
                self.message = f"Capture error: {exc}"
        finally:
            if camera is not None:
                with self._camera_lock:
                    try:
                        camera.stop()
                    finally:
                        camera.close()
            with self._lock:
                self._camera = None
                self.running = False

    @staticmethod
    def _roi_tuple(request: StartRequest) -> Optional[tuple[int, int, int, int]]:
        if None in (request.roi_x, request.roi_y, request.roi_w, request.roi_h):
            return None
        return (int(request.roi_x), int(request.roi_y), int(request.roi_w), int(request.roi_h))

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
        self.roi_tracking_min_score = float(metrics.get("roi_tracking_min_score") or self.roi_tracking_min_score)
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

    def _new_roi_tracker(
        self,
        request: StartRequest,
        roi: Optional[tuple[int, int, int, int]],
    ) -> Optional[dict]:
        if not (request.roi_tracking and roi is not None):
            return None
        x, y, width, height = roi
        return {
            "template": None,
            "initial_roi": (x, y, width, height),
            "current_roi": (x, y, width, height),
            "success": False,
            "score": None,
        }

    def _detect_motion_with_tracking(
        self,
        frame,
        background,
        pixel_difference: int,
        motion_ratio: float,
        roi: Optional[tuple[int, int, int, int]],
        roi_tracker: Optional[dict],
        request: StartRequest,
    ):
        active_roi = self._tracking_roi_for_frame(frame, roi_tracker, request) if roi_tracker else roi
        metrics, detected, background = self._detect_motion(
            frame,
            background,
            pixel_difference,
            motion_ratio,
            active_roi,
        )
        metrics.update(self._tracking_metrics(roi_tracker, active_roi, request))
        return metrics, detected, background

    def _tracking_roi_for_frame(
        self,
        frame,
        tracker: Optional[dict],
        request: StartRequest,
    ) -> Optional[tuple[int, int, int, int]]:
        if tracker is None:
            return None
        import numpy as np

        luminance = frame[:MONITOR_SIZE[1], :MONITOR_SIZE[0]].astype(np.float32)
        current_roi = tracker["current_roi"]
        x, y, width, height = current_roi
        if tracker["template"] is None:
            tracker["template"] = luminance[y:y + height, x:x + width].copy()
            tracker["score"] = 1.0
            tracker["success"] = True
            return current_roi

        best_roi, best_score = self._match_template_near_roi(
            luminance,
            tracker["template"],
            current_roi,
            request.roi_search_margin,
        )
        tracker["score"] = best_score
        if best_roi is not None and best_score is not None and best_score >= request.roi_tracking_min_score:
            tracker["current_roi"] = best_roi
            tracker["success"] = True
        else:
            tracker["success"] = False
        return tracker["current_roi"]

    @staticmethod
    def _match_template_near_roi(
        luminance,
        template,
        current_roi: tuple[int, int, int, int],
        search_margin: int,
    ) -> tuple[Optional[tuple[int, int, int, int]], Optional[float]]:
        import numpy as np

        x, y, width, height = current_roi
        margin = max(0, int(search_margin))
        search_x0 = max(0, x - margin)
        search_y0 = max(0, y - margin)
        search_x1 = min(MONITOR_SIZE[0], x + width + margin)
        search_y1 = min(MONITOR_SIZE[1], y + height + margin)
        search = luminance[search_y0:search_y1, search_x0:search_x1]
        if search.shape[0] < height or search.shape[1] < width:
            return current_roi, None

        try:
            import cv2  # type: ignore

            result = cv2.matchTemplate(search.astype(np.float32), template.astype(np.float32), cv2.TM_CCOEFF_NORMED)
            _, best_score, _, best_location = cv2.minMaxLoc(result)
            best_x = search_x0 + int(best_location[0])
            best_y = search_y0 + int(best_location[1])
            return (best_x, best_y, width, height), float(best_score)
        except Exception:
            pass

        template_small = template
        search_small = search
        scale = max(1, min(width, height) // 80)
        if scale > 1:
            template_small = template[::scale, ::scale]
            search_small = search[::scale, ::scale]
        th, tw = template_small.shape
        sh, sw = search_small.shape
        if sh < th or sw < tw:
            return current_roi, None
        template_centered = template_small - float(template_small.mean())
        template_norm = float(np.sqrt((template_centered * template_centered).sum()))
        if template_norm <= 1e-6:
            return current_roi, None
        best_score = -1.0
        best_xy = (0, 0)
        for yy in range(0, sh - th + 1):
            for xx in range(0, sw - tw + 1):
                patch = search_small[yy:yy + th, xx:xx + tw]
                patch_centered = patch - float(patch.mean())
                patch_norm = float(np.sqrt((patch_centered * patch_centered).sum()))
                if patch_norm <= 1e-6:
                    continue
                score = float((template_centered * patch_centered).sum() / (template_norm * patch_norm))
                if score > best_score:
                    best_score = score
                    best_xy = (xx, yy)
        best_x = search_x0 + int(best_xy[0] * scale)
        best_y = search_y0 + int(best_xy[1] * scale)
        return (
            max(0, min(best_x, MONITOR_SIZE[0] - width)),
            max(0, min(best_y, MONITOR_SIZE[1] - height)),
            width,
            height,
        ), best_score

    @staticmethod
    def _tracking_metrics(
        tracker: Optional[dict],
        active_roi: Optional[tuple[int, int, int, int]],
        request: StartRequest,
    ) -> dict:
        initial = tracker["initial_roi"] if tracker else None
        tracked = tracker["current_roi"] if tracker else active_roi
        shift_x = tracked[0] - initial[0] if initial and tracked else None
        shift_y = tracked[1] - initial[1] if initial and tracked else None
        return {
            "roi_tracking": bool(tracker is not None),
            "roi_tracking_success": bool(tracker.get("success")) if tracker else False,
            "roi_tracking_score": tracker.get("score") if tracker else None,
            "roi_search_margin": request.roi_search_margin,
            "roi_tracking_min_score": request.roi_tracking_min_score,
            "initial_roi_x": initial[0] if initial else None,
            "initial_roi_y": initial[1] if initial else None,
            "initial_roi_w": initial[2] if initial else None,
            "initial_roi_h": initial[3] if initial else None,
            "tracked_roi_x": tracked[0] if tracked else None,
            "tracked_roi_y": tracked[1] if tracked else None,
            "tracked_roi_w": tracked[2] if tracked else None,
            "tracked_roi_h": tracked[3] if tracked else None,
            "roi_shift_x": shift_x,
            "roi_shift_y": shift_y,
        }

    @staticmethod
    def _detect_motion(
        frame,
        background,
        pixel_difference: int,
        motion_ratio: float,
        roi: Optional[tuple[int, int, int, int]] = None,
    ):
        import numpy as np

        full_luminance = frame[:MONITOR_SIZE[1], :MONITOR_SIZE[0]].astype(np.float32)
        roi_used = roi is not None
        if roi_used:
            x, y, width, height = roi
            luminance = full_luminance[y:y + height, x:x + width]
        else:
            x, y, width, height = None, None, None, None
            luminance = full_luminance
        mean_brightness = float(luminance.mean())
        metrics = {
            "motion_score": None,
            "changed_area_ratio": None,
            "mean_brightness": mean_brightness,
            "brightness_delta": None,
            "roi_used": roi_used,
            "roi_x": x,
            "roi_y": y,
            "roi_w": width,
            "roi_h": height,
            "wind_like_motion": False,
            "num_blobs": 0,
            "largest_blob_area": 0,
            "largest_blob_ratio": None,
            "small_blob_count": 0,
            "motion_type": "none",
        }
        if background is None:
            return metrics, False, luminance

        changed = np.abs(luminance - background) >= pixel_difference
        changed_area_ratio = float(changed.mean())
        brightness_delta = abs(float(mean_brightness - float(background.mean())))
        blob_metrics = TimelapseController._blob_metrics(changed)
        motion_type = TimelapseController._classify_motion(
            changed_area_ratio=changed_area_ratio,
            brightness_delta=brightness_delta,
            largest_blob_ratio=blob_metrics["largest_blob_ratio"] or 0.0,
            small_blob_count=blob_metrics["small_blob_count"],
            motion_ratio=motion_ratio,
        )
        metrics.update(
            {
                "motion_score": changed_area_ratio,
                "changed_area_ratio": changed_area_ratio,
                "brightness_delta": brightness_delta,
                "wind_like_motion": motion_type == "wind_like_large_motion" or changed_area_ratio >= 0.20,
                **blob_metrics,
                "motion_type": motion_type,
            }
        )
        detected = motion_type == "small_object_motion"
        if not detected:
            background = (background * 0.9) + (luminance * 0.1)
        return metrics, detected, background

    @staticmethod
    def _blob_metrics(mask) -> dict:
        height, width = mask.shape
        total_pixels = height * width
        visited = mask.copy()
        num_blobs = 0
        largest_blob_area = 0
        small_blob_count = 0
        small_blob_max = max(20, int(total_pixels * 0.03))

        for start_y, start_x in zip(*mask.nonzero()):
            if not visited[start_y, start_x]:
                continue
            num_blobs += 1
            visited[start_y, start_x] = False
            area = 0
            stack = [(int(start_y), int(start_x))]
            while stack:
                y, x = stack.pop()
                area += 1
                for next_y, next_x in (
                    (y - 1, x),
                    (y + 1, x),
                    (y, x - 1),
                    (y, x + 1),
                    (y - 1, x - 1),
                    (y - 1, x + 1),
                    (y + 1, x - 1),
                    (y + 1, x + 1),
                ):
                    if 0 <= next_y < height and 0 <= next_x < width and visited[next_y, next_x]:
                        visited[next_y, next_x] = False
                        stack.append((next_y, next_x))
            largest_blob_area = max(largest_blob_area, area)
            if 4 <= area <= small_blob_max:
                small_blob_count += 1

        largest_blob_ratio = (largest_blob_area / total_pixels) if total_pixels else None
        return {
            "num_blobs": num_blobs,
            "largest_blob_area": largest_blob_area,
            "largest_blob_ratio": largest_blob_ratio,
            "small_blob_count": small_blob_count,
        }

    @staticmethod
    def _classify_motion(
        changed_area_ratio: float,
        brightness_delta: float,
        largest_blob_ratio: float,
        small_blob_count: int,
        motion_ratio: float,
    ) -> str:
        if changed_area_ratio < motion_ratio:
            return "none"
        if abs(brightness_delta) >= 20 and changed_area_ratio >= 0.05:
            return "global_brightness_change"
        if changed_area_ratio >= 0.20 or largest_blob_ratio >= 0.15:
            return "wind_like_large_motion"
        if small_blob_count > 0:
            return "small_object_motion"
        return "noisy_motion"

    @staticmethod
    def _write_metric(
        captured_at: datetime,
        image_path: Optional[Path],
        interval_sec: float,
        score: Optional[float],
        metrics: dict,
        insect_candidate: bool,
        reason: str,
        request: Optional[StartRequest] = None,
    ) -> None:
        write_header = not METRICS_PATH.exists()
        with METRICS_PATH.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if write_header:
                writer.writerow(
                    [
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
                    ]
                )
            writer.writerow(
                [
                    captured_at.isoformat(timespec="seconds"),
                    "" if image_path is None else image_path.name,
                    interval_sec,
                    "" if score is None else f"{score:.6f}",
                    insect_candidate,
                    reason,
                    DEVICE_ID,
                    DEVICE_NAME,
                    CAMERA_LABEL,
                    CAMERA_MODEL,
                    CAMERA_PROFILE,
                    IS_AI_CAMERA,
                    IS_NOIR,
                    IS_WIDE,
                    "" if request is None or request.site_id is None else request.site_id,
                    "" if request is None or request.flower_id is None else request.flower_id,
                    "" if request is None or request.plant_species is None else request.plant_species,
                    "" if request is None or request.observer is None else request.observer,
                    "" if request is None or request.notes is None else request.notes,
                    "" if request is None or request.comparison_session_id is None else request.comparison_session_id,
                    "" if request is None or request.camera_role is None else request.camera_role,
                    "" if request is None or request.method_mode is None else request.method_mode,
                    TimelapseController._metric_value(metrics, "changed_area_ratio"),
                    TimelapseController._metric_value(metrics, "mean_brightness"),
                    TimelapseController._metric_value(metrics, "brightness_delta"),
                    bool(metrics.get("wind_like_motion")),
                    TimelapseController._metric_value(metrics, "num_blobs"),
                    TimelapseController._metric_value(metrics, "largest_blob_area"),
                    TimelapseController._metric_value(metrics, "largest_blob_ratio"),
                    TimelapseController._metric_value(metrics, "small_blob_count"),
                    TimelapseController._metric_value(metrics, "motion_type"),
                    bool(metrics.get("roi_used")),
                    TimelapseController._metric_value(metrics, "roi_x"),
                    TimelapseController._metric_value(metrics, "roi_y"),
                    TimelapseController._metric_value(metrics, "roi_w"),
                    TimelapseController._metric_value(metrics, "roi_h"),
                    bool(metrics.get("roi_tracking")),
                    bool(metrics.get("roi_tracking_success")),
                    TimelapseController._metric_value(metrics, "roi_tracking_score"),
                    TimelapseController._metric_value(metrics, "roi_search_margin"),
                    TimelapseController._metric_value(metrics, "roi_tracking_min_score"),
                    TimelapseController._metric_value(metrics, "initial_roi_x"),
                    TimelapseController._metric_value(metrics, "initial_roi_y"),
                    TimelapseController._metric_value(metrics, "initial_roi_w"),
                    TimelapseController._metric_value(metrics, "initial_roi_h"),
                    TimelapseController._metric_value(metrics, "tracked_roi_x"),
                    TimelapseController._metric_value(metrics, "tracked_roi_y"),
                    TimelapseController._metric_value(metrics, "tracked_roi_w"),
                    TimelapseController._metric_value(metrics, "tracked_roi_h"),
                    TimelapseController._metric_value(metrics, "roi_shift_x"),
                    TimelapseController._metric_value(metrics, "roi_shift_y"),
                ]
            )

    @staticmethod
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
        request: StartRequest,
    ) -> None:
        write_header = not OBSERVATION_LOG_PATH.exists()
        with OBSERVATION_LOG_PATH.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if write_header:
                writer.writerow(
                    [
                        "timestamp",
                        "capture_type",
                        "image_filename",
                        "scheduled_interval_sec",
                        "scan_interval_sec",
                        "motion_score",
                        "motion_candidate",
                        "reason",
                        "device_id",
                        "device_name",
                        "camera_label",
                        "camera_model",
                        "camera_profile",
                        "is_ai_camera",
                        "is_noir",
                        "is_wide",
                        "site_id",
                        "flower_id",
                        "plant_species",
                        "observer",
                        "notes",
                        "comparison_session_id",
                        "camera_role",
                        "method_mode",
                        "changed_area_ratio",
                        "mean_brightness",
                        "brightness_delta",
                        "wind_like_motion",
                        "num_blobs",
                        "largest_blob_area",
                        "largest_blob_ratio",
                        "small_blob_count",
                        "motion_type",
                        "roi_used",
                        "roi_x",
                        "roi_y",
                        "roi_w",
                        "roi_h",
                        "roi_tracking",
                        "roi_tracking_success",
                        "roi_tracking_score",
                        "roi_search_margin",
                        "roi_tracking_min_score",
                        "initial_roi_x",
                        "initial_roi_y",
                        "initial_roi_w",
                        "initial_roi_h",
                        "tracked_roi_x",
                        "tracked_roi_y",
                        "tracked_roi_w",
                        "tracked_roi_h",
                        "roi_shift_x",
                        "roi_shift_y",
                    ]
                )
            writer.writerow(
                [
                    captured_at.isoformat(timespec="seconds"),
                    capture_type,
                    "" if image_path is None else image_path.name,
                    scheduled_interval_sec,
                    scan_interval_sec,
                    "" if score is None else f"{score:.6f}",
                    insect_candidate,
                    reason,
                    DEVICE_ID,
                    DEVICE_NAME,
                    CAMERA_LABEL,
                    CAMERA_MODEL,
                    CAMERA_PROFILE,
                    IS_AI_CAMERA,
                    IS_NOIR,
                    IS_WIDE,
                    "" if request.site_id is None else request.site_id,
                    "" if request.flower_id is None else request.flower_id,
                    "" if request.plant_species is None else request.plant_species,
                    "" if request.observer is None else request.observer,
                    "" if request.notes is None else request.notes,
                    "" if request.comparison_session_id is None else request.comparison_session_id,
                    "" if request.camera_role is None else request.camera_role,
                    "" if request.method_mode is None else request.method_mode,
                    TimelapseController._metric_value(metrics, "changed_area_ratio"),
                    TimelapseController._metric_value(metrics, "mean_brightness"),
                    TimelapseController._metric_value(metrics, "brightness_delta"),
                    bool(metrics.get("wind_like_motion")),
                    TimelapseController._metric_value(metrics, "num_blobs"),
                    TimelapseController._metric_value(metrics, "largest_blob_area"),
                    TimelapseController._metric_value(metrics, "largest_blob_ratio"),
                    TimelapseController._metric_value(metrics, "small_blob_count"),
                    TimelapseController._metric_value(metrics, "motion_type"),
                    bool(metrics.get("roi_used")),
                    TimelapseController._metric_value(metrics, "roi_x"),
                    TimelapseController._metric_value(metrics, "roi_y"),
                    TimelapseController._metric_value(metrics, "roi_w"),
                    TimelapseController._metric_value(metrics, "roi_h"),
                    bool(metrics.get("roi_tracking")),
                    bool(metrics.get("roi_tracking_success")),
                    TimelapseController._metric_value(metrics, "roi_tracking_score"),
                    TimelapseController._metric_value(metrics, "roi_search_margin"),
                    TimelapseController._metric_value(metrics, "roi_tracking_min_score"),
                    TimelapseController._metric_value(metrics, "initial_roi_x"),
                    TimelapseController._metric_value(metrics, "initial_roi_y"),
                    TimelapseController._metric_value(metrics, "initial_roi_w"),
                    TimelapseController._metric_value(metrics, "initial_roi_h"),
                    TimelapseController._metric_value(metrics, "tracked_roi_x"),
                    TimelapseController._metric_value(metrics, "tracked_roi_y"),
                    TimelapseController._metric_value(metrics, "tracked_roi_w"),
                    TimelapseController._metric_value(metrics, "tracked_roi_h"),
                    TimelapseController._metric_value(metrics, "roi_shift_x"),
                    TimelapseController._metric_value(metrics, "roi_shift_y"),
                ]
            )

    @staticmethod
    def _write_event_log(
        captured_at: datetime,
        image_path: Optional[Path],
        metrics: dict,
        request: StartRequest,
    ) -> None:
        write_header = not EVENT_LOG_PATH.exists()
        with EVENT_LOG_PATH.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if write_header:
                writer.writerow(EVENT_LOG_COLUMNS)
            writer.writerow(
                [
                    f"event_{captured_at.strftime('%Y%m%d_%H%M%S_%f')}_{DEVICE_ID}",
                    captured_at.isoformat(timespec="seconds"),
                    "" if image_path is None else image_path.name,
                    DEVICE_ID,
                    DEVICE_NAME,
                    CAMERA_LABEL,
                    CAMERA_MODEL,
                    CAMERA_PROFILE,
                    IS_AI_CAMERA,
                    IS_NOIR,
                    IS_WIDE,
                    "" if request.site_id is None else request.site_id,
                    "" if request.flower_id is None else request.flower_id,
                    "" if request.plant_species is None else request.plant_species,
                    "" if request.observer is None else request.observer,
                    "" if request.notes is None else request.notes,
                    "" if request.comparison_session_id is None else request.comparison_session_id,
                    "" if request.camera_role is None else request.camera_role,
                    "" if request.method_mode is None else request.method_mode,
                    TimelapseController._metric_value(metrics, "motion_score"),
                    TimelapseController._metric_value(metrics, "changed_area_ratio"),
                    TimelapseController._metric_value(metrics, "mean_brightness"),
                    TimelapseController._metric_value(metrics, "brightness_delta"),
                    bool(metrics.get("wind_like_motion")),
                    TimelapseController._metric_value(metrics, "num_blobs"),
                    TimelapseController._metric_value(metrics, "largest_blob_area"),
                    TimelapseController._metric_value(metrics, "largest_blob_ratio"),
                    TimelapseController._metric_value(metrics, "small_blob_count"),
                    TimelapseController._metric_value(metrics, "motion_type"),
                    bool(metrics.get("roi_used")),
                    TimelapseController._metric_value(metrics, "roi_x"),
                    TimelapseController._metric_value(metrics, "roi_y"),
                    TimelapseController._metric_value(metrics, "roi_w"),
                    TimelapseController._metric_value(metrics, "roi_h"),
                    bool(metrics.get("roi_tracking")),
                    bool(metrics.get("roi_tracking_success")),
                    TimelapseController._metric_value(metrics, "roi_tracking_score"),
                    TimelapseController._metric_value(metrics, "roi_search_margin"),
                    TimelapseController._metric_value(metrics, "roi_tracking_min_score"),
                    TimelapseController._metric_value(metrics, "initial_roi_x"),
                    TimelapseController._metric_value(metrics, "initial_roi_y"),
                    TimelapseController._metric_value(metrics, "initial_roi_w"),
                    TimelapseController._metric_value(metrics, "initial_roi_h"),
                    TimelapseController._metric_value(metrics, "tracked_roi_x"),
                    TimelapseController._metric_value(metrics, "tracked_roi_y"),
                    TimelapseController._metric_value(metrics, "tracked_roi_w"),
                    TimelapseController._metric_value(metrics, "tracked_roi_h"),
                    TimelapseController._metric_value(metrics, "roi_shift_x"),
                    TimelapseController._metric_value(metrics, "roi_shift_y"),
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

    @staticmethod
    def _metric_value(metrics: dict, key: str):
        value = metrics.get(key)
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.6f}"
        return value

    @staticmethod
    def _register_label(image_path: Path, label: str, source: str) -> None:
        if label not in {"positive", "negative"}:
            raise ValueError("Invalid image label.")
        target_dir = POSITIVE_DIR if label == "positive" else NEGATIVE_DIR
        other_dir = NEGATIVE_DIR if label == "positive" else POSITIVE_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        other_dir.mkdir(parents=True, exist_ok=True)
        other_path = other_dir / image_path.name
        if other_path.is_file():
            other_path.unlink()
        target_path = target_dir / image_path.name
        if not target_path.exists():
            try:
                os.link(image_path, target_path)
            except OSError:
                shutil.copy2(image_path, target_path)
        write_header = not LABEL_LOG_PATH.exists()
        with LABEL_LOG_PATH.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if write_header:
                writer.writerow(["timestamp", "image_filename", "label", "source"])
            writer.writerow([datetime.now().astimezone().isoformat(timespec="seconds"), image_path.name, label, source])

    @staticmethod
    def _label_index() -> dict[str, dict[str, str]]:
        labels: dict[str, dict[str, str]] = {}
        if not LABEL_LOG_PATH.is_file():
            return labels
        try:
            with LABEL_LOG_PATH.open("r", newline="", encoding="utf-8") as csv_file:
                for row in csv.DictReader(csv_file):
                    filename = row.get("image_filename", "")
                    label = row.get("label", "")
                    source = row.get("source", "")
                    if filename:
                        labels[filename] = {"label": label, "source": source}
        except OSError:
            return labels
        return labels

    @staticmethod
    def _review_status(source: Optional[str]) -> str:
        if source in {"manual_ipad_review", "manual_confirmed"}:
            return "reviewed"
        if source:
            return "auto"
        return "unlabeled"

    @staticmethod
    def _label_captured_image(image_path: Path, motion_label: str, ml_assist_mode: bool) -> None:
        label = motion_label
        source = "motion_auto"
        if ml_assist_mode and MODEL_PATH.is_file():
            predicted_label = trainer.predict(image_path)
            if predicted_label is not None:
                label = predicted_label
                source = "field_ml_prediction"
        TimelapseController._register_label(image_path, label, source)

    @staticmethod
    def _remove_label(filename: str) -> None:
        for directory in (POSITIVE_DIR, NEGATIVE_DIR, LEGACY_CANDIDATE_DIR):
            path = directory / filename
            if path.is_file():
                path.unlink()

    @staticmethod
    def migrate_legacy_candidates() -> None:
        if not LEGACY_CANDIDATE_DIR.is_dir():
            return
        for candidate_path in LEGACY_CANDIDATE_DIR.iterdir():
            original_path = IMAGE_DIR / candidate_path.name
            if candidate_path.suffix.lower() in {".jpg", ".jpeg"} and original_path.is_file():
                TimelapseController._register_label(original_path, "positive", "legacy_motion_candidate")

    @staticmethod
    def _save_autonomous_request(request: StartRequest) -> None:
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


class BinaryTrainer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.running = False
        self.trained_at: Optional[str] = None
        self.validation_accuracy: Optional[float] = None
        self.message = "No model trained yet. Auto labels can be used; correct obvious mistakes before training."

    def status(self) -> TrainingStatusResponse:
        POSITIVE_DIR.mkdir(parents=True, exist_ok=True)
        NEGATIVE_DIR.mkdir(parents=True, exist_ok=True)
        positive_count = sum(1 for path in POSITIVE_DIR.iterdir() if path.suffix.lower() in {".jpg", ".jpeg"})
        negative_count = sum(1 for path in NEGATIVE_DIR.iterdir() if path.suffix.lower() in {".jpg", ".jpeg"})
        label_index = TimelapseController._label_index()
        existing_labeled = {
            path.name
            for directory in (POSITIVE_DIR, NEGATIVE_DIR)
            for path in directory.iterdir()
            if path.suffix.lower() in {".jpg", ".jpeg"}
        }
        reviewed_count = sum(
            1 for filename, data in label_index.items()
            if filename in existing_labeled and TimelapseController._review_status(data.get("source")) == "reviewed"
        )
        auto_labeled_count = sum(
            1 for filename, data in label_index.items()
            if filename in existing_labeled and TimelapseController._review_status(data.get("source")) == "auto"
        )
        if MODEL_INFO_PATH.is_file() and self.trained_at is None:
            try:
                model_info = json.loads(MODEL_INFO_PATH.read_text(encoding="utf-8"))
                self.trained_at = model_info.get("trained_at")
                self.validation_accuracy = model_info.get("validation_accuracy")
            except (OSError, json.JSONDecodeError):
                pass
        with self._lock:
            return TrainingStatusResponse(
                running=self.running,
                positive_count=positive_count,
                negative_count=negative_count,
                auto_labeled_count=auto_labeled_count,
                reviewed_count=reviewed_count,
                model_available=MODEL_PATH.is_file(),
                trained_at=self.trained_at,
                validation_accuracy=self.validation_accuracy,
                message=self.message,
            )

    def start(self) -> TrainingStatusResponse:
        status = self.status()
        if status.running:
            return status
        if status.positive_count < 2 or status.negative_count < 2:
            raise ValueError("Training needs at least 2 reviewed positive and 2 reviewed negative images.")
        with self._lock:
            self.running = True
            self.message = "Training binary insect-presence model on reviewed labels."
        threading.Thread(target=self._train, name="pollipi-binary-training", daemon=True).start()
        return self.status()

    def reset_model(self) -> TrainingStatusResponse:
        with self._lock:
            if self.running:
                raise ValueError("Cannot discard model while training is running.")
            for path in (MODEL_PATH, MODEL_INFO_PATH):
                if path.is_file():
                    path.unlink()
            self.trained_at = None
            self.validation_accuracy = None
            self.message = "Model discarded. Reviewed labels are retained for later retraining."
        return self.status()

    def _train(self) -> None:
        try:
            import cv2
            import numpy as np

            samples = []
            labels = []
            for label, directory in ((1, POSITIVE_DIR), (0, NEGATIVE_DIR)):
                for image_path in sorted(directory.iterdir()):
                    if image_path.suffix.lower() not in {".jpg", ".jpeg"}:
                        continue
                    feature = self._image_feature(image_path)
                    if feature is None:
                        continue
                    samples.append(feature)
                    labels.append(label)
            if labels.count(1) < 2 or labels.count(0) < 2:
                raise RuntimeError("Too few readable reviewed images for training.")

            features = np.asarray(samples, dtype=np.float32)
            targets = np.asarray(labels, dtype=np.int32)
            train_indices = list(range(len(targets)))
            test_indices = []
            if labels.count(1) >= 5 and labels.count(0) >= 5:
                for label in (0, 1):
                    matching = [index for index, value in enumerate(labels) if value == label]
                    test_indices.extend(matching[::5])
                train_indices = [index for index in train_indices if index not in test_indices]

            svm = cv2.ml.SVM_create()
            svm.setType(cv2.ml.SVM_C_SVC)
            svm.setKernel(cv2.ml.SVM_RBF)
            svm.setC(2.0)
            svm.setGamma(0.01)
            svm.train(features[train_indices], cv2.ml.ROW_SAMPLE, targets[train_indices])
            accuracy = None
            if test_indices:
                _, prediction = svm.predict(features[test_indices])
                accuracy = float((prediction.reshape(-1).astype(np.int32) == targets[test_indices]).mean())
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            svm.save(str(MODEL_PATH))
            trained_at = datetime.now().astimezone().isoformat(timespec="seconds")
            MODEL_INFO_PATH.write_text(
                json.dumps(
                    {
                        "trained_at": trained_at,
                        "positive_count": labels.count(1),
                        "negative_count": labels.count(0),
                        "validation_accuracy": accuracy,
                        "feature": "HOG grayscale 64x64",
                        "classifier": "OpenCV SVM RBF",
                    },
                    ensure_ascii=True,
                    indent=2,
                ),
                encoding="utf-8",
            )
            with self._lock:
                self.trained_at = trained_at
                self.validation_accuracy = accuracy
                self.message = (
                    "Training complete. Validation accuracy is shown only after enough reviewed images."
                    if accuracy is None
                    else f"Training complete. Hold-out accuracy: {accuracy:.1%}."
                )
        except Exception as exc:
            with self._lock:
                self.message = f"Training error: {exc}"
        finally:
            with self._lock:
                self.running = False

    @staticmethod
    def _image_feature(image_path: Path):
        import cv2

        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            return None
        resized = cv2.resize(image, (64, 64))
        hog = cv2.HOGDescriptor((64, 64), (16, 16), (8, 8), (8, 8), 9)
        return hog.compute(resized).reshape(-1)

    def predict(self, image_path: Path) -> Optional[str]:
        if not MODEL_PATH.is_file():
            return None
        try:
            import cv2
            import numpy as np

            feature = self._image_feature(image_path)
            if feature is None:
                return None
            svm = cv2.ml.SVM_load(str(MODEL_PATH))
            _, prediction = svm.predict(np.asarray([feature], dtype=np.float32))
            return "positive" if int(prediction.reshape(-1)[0]) == 1 else "negative"
        except Exception:
            return None


trainer = BinaryTrainer()


controller = TimelapseController(IMAGE_DIR)


@asynccontextmanager
async def lifespan(_: FastAPI):
    controller.migrate_legacy_candidates()
    controller.resume_autonomous()
    yield
    controller.stop(preserve_autonomous=True)


app = FastAPI(title="PolliPi Timelapse API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

if WEB_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="web-app")


@app.get("/", include_in_schema=False)
def open_app() -> RedirectResponse:
    return RedirectResponse(url="/app/")


@app.post("/start", response_model=StatusResponse)
def start_timelapse(request: StartRequest) -> StatusResponse:
    selected_modes = sum((request.auto_mode, request.motion_trigger_mode, request.hybrid_mode))
    if selected_modes > 1:
        raise HTTPException(
            status_code=400,
            detail="Choose only one of auto_mode, motion_trigger_mode, and hybrid_mode.",
        )
    validate_roi(request)
    return controller.start(request)


def validate_roi(request: StartRequest) -> None:
    roi_values = (request.roi_x, request.roi_y, request.roi_w, request.roi_h)
    if all(value is None for value in roi_values):
        if request.roi_tracking:
            raise HTTPException(status_code=400, detail="ROI tracking requires roi_x, roi_y, roi_w, and roi_h.")
        return
    if any(value is None for value in roi_values):
        raise HTTPException(status_code=400, detail="ROI requires roi_x, roi_y, roi_w, and roi_h together.")
    roi_x = int(request.roi_x)
    roi_y = int(request.roi_y)
    roi_w = int(request.roi_w)
    roi_h = int(request.roi_h)
    if roi_x < 0 or roi_y < 0 or roi_w <= 0 or roi_h <= 0:
        raise HTTPException(status_code=400, detail="ROI values must satisfy x/y >= 0 and w/h > 0.")
    if roi_x + roi_w > MONITOR_SIZE[0] or roi_y + roi_h > MONITOR_SIZE[1]:
        raise HTTPException(status_code=400, detail="ROI must fit inside the 640 x 360 monitor frame.")


@app.post("/stop", response_model=StatusResponse)
def stop_timelapse() -> StatusResponse:
    return controller.stop()


@app.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    return controller.status()


@app.get("/device", response_model=DeviceInfoResponse)
def get_device() -> DeviceInfoResponse:
    return DeviceInfoResponse(
        device_id=DEVICE_ID,
        device_name=DEVICE_NAME,
        camera_label=CAMERA_LABEL,
        camera_model=CAMERA_MODEL,
        camera_profile=CAMERA_PROFILE,
        is_ai_camera=IS_AI_CAMERA,
        is_noir=IS_NOIR,
        is_wide=IS_WIDE,
    )


@app.get("/system", response_model=SystemInfoResponse)
def get_system_info() -> SystemInfoResponse:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(IMAGE_DIR)
    throttled_raw = None
    undervoltage_now = None
    undervoltage_occurred = None
    power_message = "Battery percentage is unavailable without a telemetry-capable power source."
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        throttled_raw = result.stdout.strip()
        flags = int(throttled_raw.split("=")[-1], 16)
        undervoltage_now = bool(flags & 0x1)
        undervoltage_occurred = bool(flags & 0x10000)
        if undervoltage_now:
            power_message = "Undervoltage detected now; check battery output and cable."
        elif undervoltage_occurred:
            power_message = "Undervoltage occurred since boot; check battery output and cable."
        else:
            power_message = "Voltage OK; battery percentage requires telemetry hardware."
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        pass
    return SystemInfoResponse(
        storage_path=str(IMAGE_DIR),
        storage_total_bytes=usage.total,
        storage_used_bytes=usage.used,
        storage_free_bytes=usage.free,
        storage_percent_used=round(usage.used / usage.total * 100, 1) if usage.total else 0,
        undervoltage_now=undervoltage_now,
        undervoltage_occurred=undervoltage_occurred,
        throttled_raw=throttled_raw,
        power_message=power_message,
    )


def read_event_rows() -> list[dict[str, str]]:
    if not EVENT_LOG_PATH.is_file():
        return []
    with EVENT_LOG_PATH.open("r", newline="", encoding="utf-8") as csv_file:
        rows = [dict(row) for row in csv.DictReader(csv_file)]
    for row in rows:
        for column in EVENT_LOG_COLUMNS:
            row.setdefault(column, "")
        filename = row.get("image_filename", "")
        row["image_url"] = f"/images/{filename}" if filename else ""
    return rows


def write_event_rows(rows: list[dict[str, str]]) -> None:
    EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    extra_columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in EVENT_LOG_COLUMNS and key != "image_url" and key not in extra_columns:
                extra_columns.append(key)
    fieldnames = EVENT_LOG_COLUMNS + extra_columns
    with EVENT_LOG_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            cleaned = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(cleaned)


@app.get("/events", response_model=EventListResponse)
def list_events(
    limit: int = Query(default=50, ge=1, le=500),
    label: Optional[str] = Query(default=None),
    site_id: Optional[str] = Query(default=None),
    flower_id: Optional[str] = Query(default=None),
    comparison_session_id: Optional[str] = Query(default=None),
) -> EventListResponse:
    rows = read_event_rows()
    if label is not None:
        rows = [row for row in rows if row.get("manual_label") == label]
    if site_id is not None:
        rows = [row for row in rows if row.get("site_id") == site_id]
    if flower_id is not None:
        rows = [row for row in rows if row.get("flower_id") == flower_id]
    if comparison_session_id is not None:
        rows = [row for row in rows if row.get("comparison_session_id") == comparison_session_id]
    rows = rows[-limit:]
    rows.reverse()
    return EventListResponse(event_count=len(rows), events=rows)


@app.post("/events/{event_id}/label", response_model=EventLabelResponse)
def label_event(event_id: str, request: EventLabelRequest) -> EventLabelResponse:
    false_positive_reason = (request.false_positive_reason or "").strip()
    if false_positive_reason not in FALSE_POSITIVE_REASONS:
        raise HTTPException(status_code=400, detail="Invalid false_positive_reason.")
    rows = read_event_rows()
    for row in rows:
        if row.get("event_id") == event_id:
            if request.manual_label is not None:
                manual_label = request.manual_label.strip()
                if manual_label not in {"insect", "non_insect", "unclear"}:
                    raise HTTPException(status_code=400, detail="manual_label must be insect, non_insect, or unclear.")
                row["manual_label"] = manual_label
                if manual_label == "insect":
                    false_positive_reason = ""
            if request.manual_taxon is not None:
                row["manual_taxon"] = request.manual_taxon.strip()
            if request.false_positive_reason is not None:
                row["false_positive_reason"] = false_positive_reason
            if request.manual_notes is not None:
                row["manual_notes"] = request.manual_notes.strip()
            row["reviewed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            write_event_rows(rows)
            return EventLabelResponse(
                event_id=event_id,
                manual_label=row["manual_label"],
                manual_taxon=row["manual_taxon"],
                false_positive_reason=row["false_positive_reason"],
                manual_notes=row["manual_notes"],
                reviewed_at=row["reviewed_at"],
                message="Event review label saved.",
            )
    raise HTTPException(status_code=404, detail="Event not found.")


@app.get("/events/export_labels.csv")
def export_event_labels() -> Response:
    rows = [row for row in read_event_rows() if row.get("manual_label")]
    output = io.StringIO()
    fieldnames = [
        "event_id", "timestamp", "image_filename",
        "manual_label", "manual_taxon", "false_positive_reason", "manual_notes",
        "device_id", "device_name", "camera_label", "camera_model", "camera_profile",
        "site_id", "flower_id", "plant_species", "observer", "comparison_session_id", "camera_role", "method_mode",
        "motion_score", "changed_area_ratio", "brightness_delta", "motion_type",
        "roi_used", "roi_x", "roi_y", "roi_w", "roi_h", "reviewed_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=event_labels.csv"},
    )


@app.get("/training/status", response_model=TrainingStatusResponse)
def get_training_status() -> TrainingStatusResponse:
    return trainer.status()


@app.post("/training/start", response_model=TrainingStatusResponse)
def start_training() -> TrainingStatusResponse:
    if controller.status().running:
        raise HTTPException(status_code=409, detail="Stop field observation before training to save power.")
    try:
        return trainer.start()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/training/model", response_model=TrainingStatusResponse)
def discard_training_model() -> TrainingStatusResponse:
    try:
        return trainer.reset_model()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def ensure_camera_available() -> None:
    try:
        from picamera2 import Picamera2
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Picamera2 is not available: {exc}") from exc
    try:
        if not Picamera2.global_camera_info():
            raise HTTPException(
                status_code=503,
                detail="No camera is detected by Raspberry Pi OS. Check the CSI cable, camera connector, and reboot.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Camera detection failed: {exc}") from exc


@app.get("/latest")
def get_latest() -> FileResponse:
    image_path = controller.latest_image()
    if image_path is None:
        raise HTTPException(status_code=404, detail="No captured image is available.")
    return FileResponse(image_path, media_type="image/jpeg", filename=image_path.name)


@app.get("/preview")
def get_preview() -> Response:
    ensure_camera_available()
    try:
        frame = controller.preview_frame()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Preview capture failed: {exc}") from exc
    return Response(content=frame, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/roi/suggest", response_model=RoiSuggestionResponse)
def suggest_roi() -> RoiSuggestionResponse:
    model_path = Path(FLOWER_ROI_MODEL).expanduser() if FLOWER_ROI_MODEL else None
    if model_path is None or not model_path.is_file():
        return RoiSuggestionResponse(
            available=False,
            suggested=False,
            model_path=str(model_path) if model_path else None,
            message="No flower ROI model is configured. Use manual ROI drawing.",
        )
    try:
        import cv2
        import numpy as np
    except Exception:
        return RoiSuggestionResponse(
            available=False,
            suggested=False,
            model_path=str(model_path),
            message="OpenCV is not available, so automatic ROI suggestion is disabled.",
        )
    try:
        frame_bytes = controller.preview_frame()
        image_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("preview image could not be decoded")
        resized = cv2.resize(image, MONITOR_SIZE)
        detector = cv2.CascadeClassifier(str(model_path))
        if detector.empty():
            return RoiSuggestionResponse(
                available=False,
                suggested=False,
                model_path=str(model_path),
                message="The configured ROI model could not be loaded.",
            )
        boxes = detector.detectMultiScale(resized, scaleFactor=1.08, minNeighbors=3, minSize=(20, 20))
        if len(boxes) == 0:
            return RoiSuggestionResponse(
                available=True,
                suggested=False,
                model_path=str(model_path),
                message="No flower-like ROI was suggested. Use manual drawing.",
            )
        x, y, w, h = max(boxes, key=lambda item: int(item[2]) * int(item[3]))
        x = max(0, min(int(x), MONITOR_SIZE[0] - 1))
        y = max(0, min(int(y), MONITOR_SIZE[1] - 1))
        w = max(1, min(int(w), MONITOR_SIZE[0] - x))
        h = max(1, min(int(h), MONITOR_SIZE[1] - y))
        return RoiSuggestionResponse(
            available=True,
            suggested=True,
            roi_x=x,
            roi_y=y,
            roi_w=w,
            roi_h=h,
            model_path=str(model_path),
            message="Suggested ROI from the configured lightweight model. Check and edit before starting.",
        )
    except Exception as exc:
        return RoiSuggestionResponse(
            available=True,
            suggested=False,
            model_path=str(model_path),
            message=f"ROI suggestion failed safely: {exc}",
        )


@app.get("/mjpeg")
def get_mjpeg(detect: bool = Query(default=False)) -> StreamingResponse:
    ensure_camera_available()
    if detect and CAMERA_MODEL.lower() != "imx500":
        raise HTTPException(status_code=400, detail="AI detection monitor is available only on an IMX500 camera.")
    if detect and controller.status().running:
        raise HTTPException(status_code=409, detail="Stop timelapse before starting the AI detection monitor.")
    return StreamingResponse(
        controller.monitor_frames(ai_detection=detect),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


def collection_dir(collection: str) -> Path:
    if collection == "candidates":
        collection = "positive"
    directories = {"all": IMAGE_DIR, "positive": POSITIVE_DIR, "negative": NEGATIVE_DIR}
    if collection not in directories:
        raise HTTPException(status_code=400, detail="Invalid image collection.")
    return directories[collection]


def image_file(filename: str, collection: str = "all") -> Path:
    if Path(filename).name != filename or Path(filename).suffix.lower() not in {".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Invalid image filename.")
    path = collection_dir(collection) / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return path


@app.get("/images", response_model=ImageListResponse)
def list_images(
    limit: int = Query(default=40, ge=1, le=200),
    collection: str = Query(default="all"),
) -> ImageListResponse:
    if collection == "candidates":
        collection = "positive"
    image_dir = collection_dir(collection)
    image_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(
        (path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    label_index = controller._label_index()
    images = [
        ImageInfo(
            filename=path.name,
            captured_at=datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
            size_bytes=path.stat().st_size,
            url=f"/images/{path.name}?collection={collection}",
            label=label_index.get(path.name, {}).get("label") or (collection if collection in {"positive", "negative"} else None),
            label_source=label_index.get(path.name, {}).get("source"),
            review_status=controller._review_status(label_index.get(path.name, {}).get("source")),
        )
        for path in image_paths[:limit]
    ]
    return ImageListResponse(
        image_dir=str(image_dir),
        collection=collection,
        image_count=len(image_paths),
        total_size_bytes=sum(path.stat().st_size for path in image_paths),
        images=images,
    )


@app.get("/images/{filename}")
def get_image(
    filename: str,
    collection: str = Query(default="all"),
    download: bool = Query(default=False),
) -> FileResponse:
    path = image_file(filename, collection)
    return FileResponse(
        path,
        media_type="image/jpeg",
        filename=path.name if download else None,
        content_disposition_type="attachment" if download else "inline",
    )


@app.get("/exports/images.zip")
def download_images_archive(collection: str = Query(default="all")) -> FileResponse:
    if collection == "candidates":
        collection = "positive"
    image_dir = collection_dir(collection)
    image_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(
        (path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}),
        key=lambda path: path.stat().st_mtime,
    )
    prefix = f"{collection}_images"
    with tempfile.NamedTemporaryFile(
        prefix=f"pollipi_{prefix}_",
        suffix=".zip",
        dir=IMAGE_DIR.parent,
        delete=False,
    ) as temporary_file:
        archive_path = Path(temporary_file.name)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in image_paths:
            archive.write(path, arcname=f"{prefix}/{path.name}")
        if collection == "all":
            for log_path in (OBSERVATION_LOG_PATH, METRICS_PATH, EVENT_LOG_PATH, LABEL_LOG_PATH, MODEL_INFO_PATH):
                if log_path.is_file():
                    archive.write(log_path, arcname=f"logs/{log_path.name}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"pollipi_{prefix}_{timestamp}.zip",
        background=BackgroundTask(archive_path.unlink, missing_ok=True),
    )


@app.post("/images/{filename}/label", response_model=LabelResponse)
def label_image(filename: str, request: LabelRequest) -> LabelResponse:
    original_path = image_file(filename, "all")
    if request.label == "unlabeled":
        controller._remove_label(filename)
        return LabelResponse(
            filename=filename,
            label=request.label,
            label_source="manual_unlabeled",
            review_status="unlabeled",
            message="Image label removed.",
        )
    if request.label == "confirmed":
        label_index = controller._label_index()
        current_label = label_index.get(filename, {}).get("label")
        if current_label not in {"positive", "negative"}:
            if (POSITIVE_DIR / filename).is_file():
                current_label = "positive"
            elif (NEGATIVE_DIR / filename).is_file():
                current_label = "negative"
        if current_label not in {"positive", "negative"}:
            raise HTTPException(status_code=400, detail="Image has no positive/negative label to confirm.")
        controller._register_label(original_path, current_label, "manual_confirmed")
        return LabelResponse(
            filename=filename,
            label=current_label,
            label_source="manual_confirmed",
            review_status="reviewed",
            message="Auto label confirmed by reviewer.",
        )
    if request.label not in {"positive", "negative"}:
        raise HTTPException(status_code=400, detail="Label must be positive, negative, confirmed, or unlabeled.")
    controller._register_label(original_path, request.label, "manual_ipad_review")
    return LabelResponse(
        filename=filename,
        label=request.label,
        label_source="manual_ipad_review",
        review_status="reviewed",
        message="Reviewed image label saved.",
    )


@app.delete("/images/{filename}", response_model=DeleteImageResponse)
def delete_image(filename: str) -> DeleteImageResponse:
    path = image_file(filename)
    controller._remove_label(path.name)
    path.unlink()
    controller.clear_latest_if_deleted(path)
    return DeleteImageResponse(deleted=filename, message="Image deleted.")


@app.delete("/images", response_model=DeleteAllResponse)
def delete_all_images(request: DeleteAllRequest) -> DeleteAllResponse:
    if request.confirm != "DELETE_ALL":
        raise HTTPException(status_code=400, detail="Type DELETE_ALL to confirm deletion.")
    if controller.status().running:
        raise HTTPException(status_code=409, detail="Stop timelapse before deleting all images.")
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    image_paths = [
        path for path in IMAGE_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
    ]
    for path in image_paths:
        path.unlink()
    for directory in (POSITIVE_DIR, NEGATIVE_DIR, LEGACY_CANDIDATE_DIR):
        if directory.is_dir():
            for path in directory.iterdir():
                if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}:
                    path.unlink()
    controller.clear_latest_if_deleted()
    return DeleteAllResponse(deleted_count=len(image_paths), message="All images deleted.")
