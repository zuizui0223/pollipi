"""Pydantic schemas for ROI suggestion endpoint."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RoiSuggestionResponse(BaseModel):
    available: bool
    suggested: bool
    roi_x: Optional[int] = None
    roi_y: Optional[int] = None
    roi_w: Optional[int] = None
    roi_h: Optional[int] = None
    model_path: Optional[str] = None
    message: str
