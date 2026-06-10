"""Pydantic schemas for model-training endpoints."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TrainingStatusResponse(BaseModel):
    running: bool
    positive_count: int
    negative_count: int
    auto_labeled_count: int
    reviewed_count: int
    model_available: bool
    trained_at: Optional[str]
    validation_accuracy: Optional[float]
    message: str
