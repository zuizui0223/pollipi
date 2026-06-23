"""Route handlers for the active scheduled-mesh capture API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from visit_monitor_server.api.auth import require_device_secret
from visit_monitor_server.api.schemas.capture import StartRequest, StatusResponse
from visit_monitor_server.services import get_controller

router = APIRouter(tags=["capture"])


def _validate_start(request: StartRequest) -> None:
    if request.adaptive_min_interval_sec > request.adaptive_max_interval_sec:
        raise HTTPException(
            status_code=422,
            detail="adaptive_min_interval_sec must not exceed adaptive_max_interval_sec.",
        )


@router.post("/start", response_model=StatusResponse, dependencies=[Depends(require_device_secret)])
def start_timelapse(request: StartRequest) -> StatusResponse:
    _validate_start(request)
    return get_controller().start(request)


@router.post("/stop", response_model=StatusResponse, dependencies=[Depends(require_device_secret)])
def stop_timelapse() -> StatusResponse:
    return get_controller().stop()


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    return get_controller().status()
