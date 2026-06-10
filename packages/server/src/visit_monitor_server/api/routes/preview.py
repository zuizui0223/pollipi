"""Route handlers for /latest, /preview, /mjpeg."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse

from visit_monitor_server.config import CAMERA_MODEL, USE_FAKE_CAMERA
from visit_monitor_server.services import get_controller

router = APIRouter(tags=["preview"])


def _ensure_camera_available() -> None:
    """Raise 503 if the real camera cannot be accessed (skipped for fake camera)."""
    if USE_FAKE_CAMERA:
        return
    try:
        from picamera2 import Picamera2  # type: ignore
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


@router.get("/latest")
def get_latest() -> FileResponse:
    image_path = get_controller().latest_image()
    if image_path is None:
        raise HTTPException(status_code=404, detail="No captured image is available.")
    return FileResponse(image_path, media_type="image/jpeg", filename=image_path.name)


@router.get("/preview")
def get_preview() -> Response:
    _ensure_camera_available()
    try:
        frame = get_controller().preview_frame()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Preview capture failed: {exc}") from exc
    return Response(content=frame, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/mjpeg")
def get_mjpeg(detect: bool = Query(default=False)) -> StreamingResponse:
    _ensure_camera_available()
    if detect and CAMERA_MODEL.lower() != "imx500":
        raise HTTPException(status_code=400, detail="AI detection monitor is available only on an IMX500 camera.")
    if detect and get_controller().status().running:
        raise HTTPException(status_code=409, detail="Stop timelapse before starting the AI detection monitor.")
    return StreamingResponse(
        get_controller().monitor_frames(ai_detection=detect),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )
