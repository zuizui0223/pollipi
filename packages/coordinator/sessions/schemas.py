from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SessionDeviceInput(BaseModel):
    device_id: int
    camera_role: Optional[str] = None


class SessionCreateRequest(BaseModel):
    name: str = Field(default="Observation session", min_length=1, max_length=128)
    devices: list[SessionDeviceInput] = Field(default_factory=list)
    site_id: Optional[str] = None
    flower_id: Optional[str] = None
    plant_species: Optional[str] = None
    observer: Optional[str] = None
    notes: Optional[str] = None
    comparison_session_id: Optional[str] = None
    method_mode: Optional[str] = None
    interval_sec: float = Field(default=10, ge=1, le=3600)
    auto_mode: bool = False
    motion_trigger_mode: bool = False
    hybrid_mode: bool = False
    ml_assist_mode: bool = False
    autonomous_mode: bool = False
    idle_interval_sec: float = Field(default=60, ge=1, le=3600)
    detection_interval_sec: float = Field(default=3, ge=1, le=3600)
    pixel_difference: int = Field(default=30, ge=1, le=255)
    motion_ratio: float = Field(default=0.01, ge=0.0001, le=1)


class SessionUpdateRequest(SessionCreateRequest):
    name: str = Field(default="Observation session", min_length=1, max_length=128)


class SessionDeviceResponse(BaseModel):
    device_id: int
    camera_role: Optional[str] = None


class SessionResponse(BaseModel):
    id: int
    name: str
    status: str
    devices: list[SessionDeviceResponse]
    site_id: Optional[str] = None
    flower_id: Optional[str] = None
    plant_species: Optional[str] = None
    observer: Optional[str] = None
    notes: Optional[str] = None
    comparison_session_id: Optional[str] = None
    method_mode: Optional[str] = None
    interval_sec: float
    auto_mode: bool
    motion_trigger_mode: bool
    hybrid_mode: bool
    ml_assist_mode: bool
    autonomous_mode: bool
    idle_interval_sec: float
    detection_interval_sec: float
    pixel_difference: int
    motion_ratio: float
    last_result: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse] = Field(default_factory=list)

