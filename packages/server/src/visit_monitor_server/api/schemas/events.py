"""Pydantic schemas for event-log endpoints."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class EventListResponse(BaseModel):
    event_count: int
    events: list[dict[str, str]]


class EventLabelRequest(BaseModel):
    manual_label: Optional[str] = None
    manual_taxon: Optional[str] = None
    false_positive_reason: Optional[str] = None
    manual_notes: Optional[str] = None


class EventLabelResponse(BaseModel):
    event_id: str
    manual_label: str
    manual_taxon: str
    false_positive_reason: str
    manual_notes: str
    reviewed_at: str
    message: str
