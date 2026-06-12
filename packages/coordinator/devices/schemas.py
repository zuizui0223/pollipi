from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DeviceCreateRequest(BaseModel):
    address: str = ""
    base_url: str
    display_name: Optional[str] = None
    device_secret: Optional[str] = None
    verify_connection: bool = True


class DeviceUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    address: Optional[str] = None
    base_url: Optional[str] = None
    device_secret: Optional[str] = None
    verify_connection: bool = True


class DeviceResponse(BaseModel):
    id: int
    address: str
    base_url: str
    api_path_prefix: str
    device_id: str
    device_name: str
    display_name: str
    camera_label: str
    camera_model: str
    camera_profile: str
    is_ai_camera: bool
    is_noir: bool
    is_wide: bool
    last_status: Optional[dict[str, Any]] = None
    last_error: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DeviceListResponse(BaseModel):
    devices: list[DeviceResponse] = Field(default_factory=list)


class ProxyErrorResponse(BaseModel):
    detail: str

