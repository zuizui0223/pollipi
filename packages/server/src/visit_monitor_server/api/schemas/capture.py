"""Pydantic schemas for capture (start/stop/status) endpoints."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    interval_sec: float = Field(..., ge=1, le=3600)
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
    control_roi_x: Optional[int] = None
    control_roi_y: Optional[int] = None
    control_roi_w: Optional[int] = None
    control_roi_h: Optional[int] = None
    roi_grid_rows: int = Field(default=4, ge=1, le=12)
    roi_grid_cols: int = Field(default=4, ge=1, le=12)
    roi_tracking: bool = False
    roi_search_margin: int = Field(default=30, ge=0, le=160)
    roi_tracking_min_score: float = Field(default=0.45, ge=-1.0, le=1.0)
    auto_mode: bool = False
    motion_trigger_mode: bool = False
    hybrid_mode: bool = False
    ml_assist_mode: bool = False
    autonomous_mode: bool = False
    adaptive_timelapse_mode: bool = False
    adaptive_min_interval_sec: float = Field(default=15, ge=1, le=3600)
    adaptive_window_sec: float = Field(default=300, ge=60, le=3600)
    idle_interval_sec: float = Field(default=60, ge=1, le=3600)
    detection_interval_sec: float = Field(default=3, ge=1, le=3600)
    pixel_difference: int = Field(default=30, ge=1, le=255)
    motion_ratio: float = Field(default=0.01, ge=0.0001, le=1)


class StatusResponse(BaseModel):
    running: bool
    lifecycle_state: str = "stopped"
    last_error: Optional[str] = None
    preview_subscriber_count: int = 0
    preview_latest_frame_age_sec: Optional[float] = None
    preview_producer_state: str = "idle"
    interval_sec: Optional[float]
    capture_count: int
    last_capture_time: Optional[str]
    last_image: Optional[str]
    message: str
    auto_mode: bool
    motion_trigger_mode: bool
    hybrid_mode: bool
    ml_assist_mode: bool
    autonomous_mode: bool
    adaptive_timelapse_mode: bool = False
    motion_score: Optional[float]
    changed_area_ratio: Optional[float]
    mean_brightness: Optional[float]
    brightness_delta: Optional[float]
    wind_like_motion: bool
    num_blobs: int
    largest_blob_area: int
    largest_blob_ratio: Optional[float]
    small_blob_count: int
    motion_type: str
    insect_candidate: bool
    detection_count: int
    event_count: int
    interval_reason: str
    device_id: str
    device_name: str
    camera_label: str
    camera_model: str
    camera_profile: str
    is_ai_camera: bool
    is_noir: bool
    is_wide: bool
    site_id: Optional[str]
    flower_id: Optional[str]
    plant_species: Optional[str]
    observer: Optional[str]
    notes: Optional[str]
    comparison_session_id: Optional[str]
    camera_role: Optional[str]
    method_mode: Optional[str]
    roi_used: bool
    roi_x: Optional[int]
    roi_y: Optional[int]
    roi_w: Optional[int]
    roi_h: Optional[int]
    roi_semantics: str = "floral_display_zone"
    control_roi_used: bool = False
    control_roi_x: Optional[int] = None
    control_roi_y: Optional[int] = None
    control_roi_w: Optional[int] = None
    control_roi_h: Optional[int] = None
    floral_zone_score: Optional[float] = None
    background_control_score: Optional[float] = None
    zone_minus_control_score: Optional[float] = None
    grid_rows: int = 4
    grid_cols: int = 4
    changed_cell_count: int = 0
    changed_cell_ratio: Optional[float] = None
    local_compactness: Optional[float] = None
    whole_frame_change_score: Optional[float] = None
    previous_frame_elapsed_sec: Optional[float] = None
    robust_background_score: Optional[float] = None
    candidate_reasons: Optional[str] = None
    mesh_decision: Optional[str] = None
    mesh_reason: Optional[str] = None
    mesh_active_cell_proportion: Optional[float] = None
    mesh_offset_agreement: Optional[float] = None
    mesh_global_synchrony: Optional[float] = None
    roi_tracking: bool
    roi_tracking_success: bool
    roi_tracking_score: Optional[float]
    roi_search_margin: int
    roi_tracking_min_score: float
    initial_roi_x: Optional[int]
    initial_roi_y: Optional[int]
    initial_roi_w: Optional[int]
    initial_roi_h: Optional[int]
    tracked_roi_x: Optional[int]
    tracked_roi_y: Optional[int]
    tracked_roi_w: Optional[int]
    tracked_roi_h: Optional[int]
    roi_shift_x: Optional[int]
    roi_shift_y: Optional[int]
