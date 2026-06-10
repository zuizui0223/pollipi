"""Pydantic schemas for image-management endpoints."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ImageInfo(BaseModel):
    filename: str
    captured_at: str
    size_bytes: int
    url: str
    label: Optional[str] = None
    label_source: Optional[str] = None
    review_status: str = "unlabeled"
    auto_category: str = "unclear"
    final_category: str = "unclear"
    category_source: str = "auto"


class ImageListResponse(BaseModel):
    image_dir: str
    collection: str
    image_count: int
    total_size_bytes: int
    images: list[ImageInfo]


class DeleteImageResponse(BaseModel):
    deleted: str
    message: str


class DeleteAllRequest(BaseModel):
    confirm: str


class DeleteAllResponse(BaseModel):
    deleted_count: int
    message: str


class LabelRequest(BaseModel):
    label: str


class LabelResponse(BaseModel):
    filename: str
    label: str
    label_source: str
    review_status: str
    message: str
