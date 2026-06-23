"""API schemas sub-package."""
from visit_monitor_server.api.schemas.capture import StartRequest, StatusResponse
from visit_monitor_server.api.schemas.device import DeviceInfoResponse, SystemInfoResponse
from visit_monitor_server.api.schemas.images import (
    DeleteAllRequest,
    DeleteAllResponse,
    DeleteImageResponse,
    ImageInfo,
    ImageListResponse,
)

__all__ = [
    "StartRequest",
    "StatusResponse",
    "DeviceInfoResponse",
    "SystemInfoResponse",
    "DeleteAllRequest",
    "DeleteAllResponse",
    "DeleteImageResponse",
    "ImageInfo",
    "ImageListResponse",
]
