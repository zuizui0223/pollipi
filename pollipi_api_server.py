"""PolliPi timelapse control API for Raspberry Pi Camera Module 3."""

from __future__ import annotations

import csv
import json
import os
import socket
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


IMAGE_DIR = Path(
    os.getenv("POLLIPI_IMAGE_DIR", str(Path.home() / "pollipi_timelapse" / "images"))
).expanduser()
METRICS_PATH = IMAGE_DIR / "adaptive_metrics.csv"
AUTONOMOUS_PATH = IMAGE_DIR.parent / "autonomous_run.json"
WEB_DIR = Path(__file__).parent / "web"
PREVIEW_PATH = Path("/tmp/pollipi_preview.jpg")
DEVICE_ID = os.getenv("POLLIPI_DEVICE_ID", socket.gethostname())
DEVICE_NAME = os.getenv("POLLIPI_DEVICE_NAME", socket.gethostname())
CAMERA_LABEL = os.getenv("POLLIPI_CAMERA_LABEL", "PolliPi Camera")
CAMERA_MODEL = os.getenv("POLLIPI_CAMERA_MODEL", "Picamera2 camera")


class StartRequest(BaseModel):
    interval_sec: float = Field(..., ge=1, le=3600)
    auto_mode: bool = False
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
    autonomous_mode: bool
    motion_score: Optional[float]
    insect_candidate: bool
    detection_count: int
    interval_reason: str


class DeviceInfoResponse(BaseModel):
    device_id: str
    device_name: str
    camera_label: str
    camera_model: str
    app_name: str = "PolliPi Field Observer"
    api_version: str = "1"


class ImageInfo(BaseModel):
    filename: str
    captured_at: str
    size_bytes: int
    url: str


class ImageListResponse(BaseModel):
    image_dir: str
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


class TimelapseController:
    def __init__(self, image_dir: Path) -> None:
        self.image_dir = image_dir
        self._lock = threading.Lock()
        self._stop_event: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._camera = None
        self._camera_lock = threading.Lock()
        self.running = False
        self.interval_sec: Optional[float] = None
        self.capture_count = 0
        self.last_capture_time: Optional[str] = None
        self.last_image: Optional[str] = None
        self.message = "Stopped."
        self.auto_mode = False
        self.autonomous_mode = False
        self.motion_score: Optional[float] = None
        self.insect_candidate = False
        self.detection_count = 0
        self.interval_reason = "Manual interval."

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
                autonomous_mode=self.autonomous_mode,
                motion_score=self.motion_score,
                insect_candidate=self.insect_candidate,
                detection_count=self.detection_count,
                interval_reason=self.interval_reason,
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
            self.auto_mode = request.auto_mode
            self.autonomous_mode = request.autonomous_mode
            self.motion_score = None
            self.insect_candidate = False
            self.detection_count = 0
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
            autonomous_mode=self.autonomous_mode,
            motion_score=self.motion_score,
            insect_candidate=self.insect_candidate,
            detection_count=self.detection_count,
            interval_reason=self.interval_reason,
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
        if camera is not None:
            with self._camera_lock:
                camera.capture_file(str(PREVIEW_PATH))
                return PREVIEW_PATH.read_bytes()

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
                return PREVIEW_PATH.read_bytes()
            finally:
                preview_camera.stop()
                preview_camera.close()

    def _capture_loop(self, stop_event: threading.Event, request: StartRequest) -> None:
        camera = None
        background = None
        try:
            from picamera2 import Picamera2

            self.image_dir.mkdir(parents=True, exist_ok=True)
            camera = Picamera2()
            camera.configure(
                camera.create_still_configuration(lores={"size": (320, 240), "format": "YUV420"})
            )
            camera.start()
            with self._lock:
                self._camera = camera

            # Give automatic exposure and white balance a moment to settle.
            if stop_event.wait(2):
                return

            with self._lock:
                self.message = "Timelapse running."

            while not stop_event.is_set():
                captured_at = datetime.now().astimezone()
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
                    score, insect_candidate, background = self._detect_motion(
                        frame,
                        background,
                        request.pixel_difference,
                        request.motion_ratio,
                    )
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
                        insect_candidate,
                        interval_reason,
                    )

                with self._lock:
                    self.capture_count += 1
                    self.interval_sec = next_interval
                    self.last_capture_time = captured_at.isoformat(timespec="seconds")
                    self.last_image = str(image_path)
                    self.message = "Timelapse running."
                    self.motion_score = score
                    self.insect_candidate = insect_candidate
                    if insect_candidate:
                        self.detection_count += 1
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
    def _detect_motion(frame, background, pixel_difference: int, motion_ratio: float):
        import numpy as np

        luminance = frame[:240, :320].astype(np.float32)
        if background is None:
            return None, False, luminance

        changed = np.abs(luminance - background) >= pixel_difference
        score = float(changed.mean())
        detected = score >= motion_ratio
        if not detected:
            background = (background * 0.9) + (luminance * 0.1)
        return score, detected, background

    @staticmethod
    def _write_metric(
        captured_at: datetime,
        image_path: Path,
        interval_sec: float,
        score: Optional[float],
        insect_candidate: bool,
        reason: str,
    ) -> None:
        write_header = not METRICS_PATH.exists()
        with METRICS_PATH.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if write_header:
                writer.writerow(
                    ["timestamp", "image_filename", "interval_sec", "motion_score", "insect_candidate", "reason"]
                )
            writer.writerow(
                [
                    captured_at.isoformat(timespec="seconds"),
                    image_path.name,
                    interval_sec,
                    "" if score is None else f"{score:.6f}",
                    insect_candidate,
                    reason,
                ]
            )

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


controller = TimelapseController(IMAGE_DIR)


@asynccontextmanager
async def lifespan(_: FastAPI):
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
    return controller.start(request)


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
    )


@app.get("/latest")
def get_latest() -> FileResponse:
    image_path = controller.latest_image()
    if image_path is None:
        raise HTTPException(status_code=404, detail="No captured image is available.")
    return FileResponse(image_path, media_type="image/jpeg", filename=image_path.name)


@app.get("/preview")
def get_preview() -> Response:
    frame = controller.preview_frame()
    return Response(content=frame, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


def image_file(filename: str) -> Path:
    if Path(filename).name != filename or Path(filename).suffix.lower() not in {".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Invalid image filename.")
    path = IMAGE_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return path


@app.get("/images", response_model=ImageListResponse)
def list_images(limit: int = Query(default=40, ge=1, le=200)) -> ImageListResponse:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(
        (path for path in IMAGE_DIR.iterdir() if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    images = [
        ImageInfo(
            filename=path.name,
            captured_at=datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
            size_bytes=path.stat().st_size,
            url=f"/images/{path.name}",
        )
        for path in image_paths[:limit]
    ]
    return ImageListResponse(
        image_dir=str(IMAGE_DIR),
        image_count=len(image_paths),
        total_size_bytes=sum(path.stat().st_size for path in image_paths),
        images=images,
    )


@app.get("/images/{filename}")
def get_image(filename: str) -> FileResponse:
    path = image_file(filename)
    return FileResponse(path, media_type="image/jpeg", filename=path.name)


@app.delete("/images/{filename}", response_model=DeleteImageResponse)
def delete_image(filename: str) -> DeleteImageResponse:
    path = image_file(filename)
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
    controller.clear_latest_if_deleted()
    return DeleteAllResponse(deleted_count=len(image_paths), message="All images deleted.")
