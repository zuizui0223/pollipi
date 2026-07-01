"""Image-store helpers for the scheduled-timelapse gallery.

The active design keeps only the scheduled timelapse images as the scientific
record. There is no positive/negative/candidate collection and no image-label
review workflow (those belonged to the removed ML training path).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from visit_monitor_server.config import get_image_dir


def image_file(filename: str) -> Path:
    """Validate *filename* and return its absolute path under the image dir.

    Raises ``HTTPException(400)`` for unsafe filenames and ``HTTPException(404)``
    if the file does not exist.
    """
    if Path(filename).name != filename or Path(filename).suffix.lower() not in {".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Invalid image filename.")
    path = get_image_dir() / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return path
