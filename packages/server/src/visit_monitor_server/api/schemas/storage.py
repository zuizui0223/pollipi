"""Pydantic schemas for the /storage (image-storage location) endpoints."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class StorageTarget(BaseModel):
    path: str
    mount: Optional[str] = None
    label: str
    kind: str
    exists: bool
    writable: bool
    is_mount: bool
    is_current: bool
    is_default: bool
    storage_total_bytes: int
    storage_used_bytes: int
    storage_free_bytes: int
    storage_percent_used: float


class StorageInfoResponse(BaseModel):
    current_path: str
    default_path: str
    capture_running: bool
    targets: list[StorageTarget]


class SetStorageRequest(BaseModel):
    # Absolute path to the new image directory. Null / empty resets to the
    # SD-card default and clears the persisted override.
    path: Optional[str] = None
