"""Pydantic schemas for the active scheduled-mesh capture API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StartRequest(BaseModel):
    """Minimal active request for scheduled timelapse and mesh shadow mode."""

    model_config = ConfigDict(extra="forbid")

    interval_sec: float = Field(..., ge=1, le=3600)
    autonomous_mode: bool = False
    adaptive_timelapse_mode: bool = False
    mesh_shadow_mode: bool = True
    adaptive_min_interval_sec: float = Field(default=15, ge=1, le=3600)
    adaptive_max_interval_sec: float = Field(default=3600, ge=1, le=3600)
    adaptive_window_sec: float = Field(default=300, ge=60, le=3600)

    site_id: Optional[str] = None
    flower_id: Optional[str] = None
    plant_species: Optional[str] = None
    observer: Optional[str] = None
    notes: Optional[str] = None
    comparison_session_id: Optional[str] = None
    camera_role: Optional[str] = None
    method_mode: Optional[str] = None


class StatusResponse(BaseModel):
    """Minimal status for the active iPad console and coordinator."""

    device_id: str
    device_name: str
    camera_label: str
    camera_model: str
    camera_profile: str
    is_ai_camera: bool
    is_noir: bool
    is_wide: bool

    running: bool
    lifecycle_state: str = "stopped"
    last_error: Optional[str] = None
    preview_subscriber_count: int = 0
    preview_latest_frame_age_sec: Optional[float] = None
    preview_producer_state: str = "idle"

    interval_sec: Optional[float] = None
    next_interval_sec: Optional[float] = None
    capture_count: int = 0
    last_capture_time: Optional[str] = None
    last_image: Optional[str] = None
    message: str = ""

    autonomous_mode: bool = False
    adaptive_timelapse_mode: bool = False
    mesh_shadow_mode: bool = True
    interval_reason: Optional[str] = None

    site_id: Optional[str] = None
    flower_id: Optional[str] = None
    plant_species: Optional[str] = None
    observer: Optional[str] = None
    notes: Optional[str] = None
    comparison_session_id: Optional[str] = None
    camera_role: Optional[str] = None
    method_mode: Optional[str] = None

    mesh_decision: Optional[str] = None
    mesh_reason: Optional[str] = None
    mesh_active_cell_proportion: Optional[float] = None
    mesh_offset_agreement: Optional[float] = None
    mesh_global_synchrony: Optional[float] = None
