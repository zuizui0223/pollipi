"""PolliPi timelapse control API for Raspberry Pi Camera Module 3."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


IMAGE_DIR = Path("/home/zuizui0223/pollipi_timelapse/images")
WEB_DIR = Path(__file__).parent / "web"


class StartRequest(BaseModel):
    interval_sec: float = Field(..., ge=1, le=3600)


class StatusResponse(BaseModel):
    running: bool
    interval_sec: Optional[float]
    capture_count: int
    last_capture_time: Optional[str]
    last_image: Optional[str]
    message: str


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


class TimelapseController:
    def __init__(self, image_dir: Path) -> None:
        self.image_dir = image_dir
        self._lock = threading.Lock()
        self._stop_event: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None
        self.running = False
        self.interval_sec: Optional[float] = None
        self.capture_count = 0
        self.last_capture_time: Optional[str] = None
        self.last_image: Optional[str] = None
        self.message = "Stopped."

    def status(self) -> StatusResponse:
        with self._lock:
            return StatusResponse(
                running=self.running,
                interval_sec=self.interval_sec,
                capture_count=self.capture_count,
                last_capture_time=self.last_capture_time,
                last_image=self.last_image,
                message=self.message,
            )

    def start(self, interval_sec: float) -> StatusResponse:
        self.stop()

        stop_event = threading.Event()
        with self._lock:
            self.running = True
            self.interval_sec = interval_sec
            self.capture_count = 0
            self.last_capture_time = None
            self.last_image = None
            self.message = "Starting timelapse."
            self._stop_event = stop_event
            self._thread = threading.Thread(
                target=self._capture_loop,
                args=(stop_event, interval_sec),
                name="pollipi-timelapse",
                daemon=True,
            )
            thread = self._thread

        thread.start()
        return self.status()

    def stop(self) -> StatusResponse:
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
            if was_active:
                self.message = "Timelapse stopped."
            return self.status_unlocked()

    def status_unlocked(self) -> StatusResponse:
        return StatusResponse(
            running=self.running,
            interval_sec=self.interval_sec,
            capture_count=self.capture_count,
            last_capture_time=self.last_capture_time,
            last_image=self.last_image,
            message=self.message,
        )

    def latest_image(self) -> Optional[Path]:
        with self._lock:
            image = self.last_image
        if image is None:
            return None
        path = Path(image)
        return path if path.is_file() else None

    def clear_latest_if_deleted(self, deleted_path: Path) -> None:
        with self._lock:
            if self.last_image == str(deleted_path):
                self.last_image = None
                self.last_capture_time = None

    def _capture_loop(self, stop_event: threading.Event, interval_sec: float) -> None:
        camera = None
        try:
            from picamera2 import Picamera2

            self.image_dir.mkdir(parents=True, exist_ok=True)
            camera = Picamera2()
            camera.configure(camera.create_still_configuration())
            camera.start()

            # Give automatic exposure and white balance a moment to settle.
            if stop_event.wait(2):
                return

            with self._lock:
                self.message = "Timelapse running."

            while not stop_event.is_set():
                captured_at = datetime.now().astimezone()
                filename = captured_at.strftime("image_%Y%m%d_%H%M%S_%f.jpg")
                image_path = self.image_dir / filename
                camera.capture_file(str(image_path))

                with self._lock:
                    self.capture_count += 1
                    self.last_capture_time = captured_at.isoformat(timespec="seconds")
                    self.last_image = str(image_path)
                    self.message = "Timelapse running."

                if stop_event.wait(interval_sec):
                    break
        except Exception as exc:
            with self._lock:
                self.message = f"Capture error: {exc}"
        finally:
            if camera is not None:
                try:
                    camera.stop()
                finally:
                    camera.close()
            with self._lock:
                self.running = False


controller = TimelapseController(IMAGE_DIR)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    controller.stop()


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
    return controller.start(request.interval_sec)


@app.post("/stop", response_model=StatusResponse)
def stop_timelapse() -> StatusResponse:
    return controller.stop()


@app.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    return controller.status()


@app.get("/latest")
def get_latest() -> FileResponse:
    image_path = controller.latest_image()
    if image_path is None:
        raise HTTPException(status_code=404, detail="No captured image is available.")
    return FileResponse(image_path, media_type="image/jpeg", filename=image_path.name)


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
