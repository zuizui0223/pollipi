"""Pydantic schemas for scheduled-timelapse image management."""
from __future__ import annotations

from pydantic import BaseModel


class ImageInfo(BaseModel):
    filename: str
    captured_at: str
    size_bytes: int
    url: str


class ImageListResponse(BaseModel):
    image_dir: str
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


class BulkDeleteImagesRequest(BaseModel):
    filenames: list[str]
