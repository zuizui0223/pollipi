"""Route handlers for /start, /stop, /status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from visit_monitor_server.api.auth import require_device_secret
from visit_monitor_server.api.schemas.capture import StartRequest, StatusResponse
from visit_monitor_server.config import ENABLE_LEGACY_ROUTES, MONITOR_SIZE
from visit_monitor_server.services import get_controller

router = APIRouter(tags=["capture"])


def _validate_roi(request: StartRequest) -> None:
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
        raise HTTPException(
            status_code=400,
            detail=f"ROI must fit inside the {MONITOR_SIZE[0]} x {MONITOR_SIZE[1]} monitor frame.",
        )


def _validate_active_start(request: StartRequest) -> None:
    if ENABLE_LEGACY_ROUTES:
        return
    if request.auto_mode or request.motion_trigger_mode or request.hybrid_mode or request.ml_assist_mode:
        raise HTTPException(
            status_code=410,
            detail="Legacy auto, motion-trigger, hybrid, and ML modes are removed from the active workflow.",
        )
    if request.roi_tracking or any(
        value is not None
        for value in (
            request.roi_x, request.roi_y, request.roi_w, request.roi_h,
            request.control_roi_x, request.control_roi_y, request.control_roi_w, request.control_roi_h,
        )
    ):
        raise HTTPException(status_code=410, detail="Manual ROI configuration is not part of the active workflow.")


@router.post("/start", response_model=StatusResponse, dependencies=[Depends(require_device_secret)])
def start_timelapse(request: StartRequest) -> StatusResponse:
    _validate_active_start(request)
    selected_modes = sum((request.auto_mode, request.motion_trigger_mode, request.hybrid_mode))
    if selected_modes > 1:
        raise HTTPException(
            status_code=400,
            detail="Choose only one of auto_mode, motion_trigger_mode, and hybrid_mode.",
        )
    _validate_roi(request)
    return get_controller().start(request)


@router.post("/stop", response_model=StatusResponse, dependencies=[Depends(require_device_secret)])
def stop_timelapse() -> StatusResponse:
    return get_controller().stop()


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    return get_controller().status()
