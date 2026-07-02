"""Pydantic schemas for device and system-info endpoints."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class BuildInfoResponse(BaseModel):
    app_version: str = "unknown"
    git_commit: str = "unknown"
    build_timestamp: str = "unknown"
    deployment_mode: str = "unknown"
    web_build_id: str = "unknown"


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
    build_info: BuildInfoResponse = BuildInfoResponse()


class SystemInfoResponse(BaseModel):
    storage_path: str
    storage_total_bytes: int
    storage_used_bytes: int
    storage_free_bytes: int
    storage_percent_used: float
    battery_percent: Optional[float] = None
    supply_voltage_v: Optional[float] = None
    undervoltage_now: Optional[bool]
    undervoltage_occurred: Optional[bool]
    throttled_raw: Optional[str]
    power_message: str
