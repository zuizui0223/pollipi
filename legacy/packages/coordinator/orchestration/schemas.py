from typing import Any, Optional

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    interval_sec: float = Field(default=10, ge=1, le=3600)
    site_id: Optional[str] = None
    flower_id: Optional[str] = None
    plant_species: Optional[str] = None
    observer: Optional[str] = None
    notes: Optional[str] = None
    comparison_session_id: Optional[str] = None
    camera_role: Optional[str] = None
    method_mode: Optional[str] = None
    roi_x: Optional[int] = None
    roi_y: Optional[int] = None
    roi_w: Optional[int] = None
    roi_h: Optional[int] = None
    roi_tracking: bool = False
    roi_search_margin: int = Field(default=30, ge=0, le=160)
    roi_tracking_min_score: float = Field(default=0.45, ge=-1.0, le=1.0)
    auto_mode: bool = False
    motion_trigger_mode: bool = False
    hybrid_mode: bool = False
    ml_assist_mode: bool = False
    autonomous_mode: bool = False
    idle_interval_sec: float = Field(default=60, ge=1, le=3600)
    detection_interval_sec: float = Field(default=3, ge=1, le=3600)
    pixel_difference: int = Field(default=30, ge=1, le=255)
    motion_ratio: float = Field(default=0.01, ge=0.0001, le=1)


class DeviceCommandResult(BaseModel):
    device_id: int
    ok: bool
    data: Optional[Any] = None
    error: Optional[str] = None


class OrchestrationResponse(BaseModel):
    ok: bool
    results: list[DeviceCommandResult]


class OrchestrationStartRequest(BaseModel):
    device_ids: Optional[list[int]] = None
    session_id: Optional[int] = None
    payload: StartRequest


class OrchestrationStopRequest(BaseModel):
    device_ids: Optional[list[int]] = None
    session_id: Optional[int] = None


class OrchestrationStatusRequest(BaseModel):
    device_ids: Optional[list[int]] = None
    session_id: Optional[int] = None

