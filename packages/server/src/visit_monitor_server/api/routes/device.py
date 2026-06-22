"""Route handlers for /device and /system."""
from __future__ import annotations

from fastapi import APIRouter

from visit_monitor_server.adapters.system_info import disk_usage, throttle_status
from visit_monitor_server.build_info import get_build_info
from visit_monitor_server.api.schemas.device import DeviceInfoResponse, SystemInfoResponse
from visit_monitor_server.config import (
    CAMERA_LABEL,
    CAMERA_MODEL,
    CAMERA_PROFILE,
    DEVICE_ID,
    DEVICE_NAME,
    IMAGE_DIR,
    IS_AI_CAMERA,
    IS_NOIR,
    IS_WIDE,
)

router = APIRouter(tags=["device"])


@router.get("/device", response_model=DeviceInfoResponse)
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
        build_info=get_build_info(),
    )


@router.get("/system", response_model=SystemInfoResponse)
def get_system_info() -> SystemInfoResponse:
    storage = disk_usage(IMAGE_DIR)
    power = throttle_status()
    return SystemInfoResponse(
        **storage,
        **power,
    )
