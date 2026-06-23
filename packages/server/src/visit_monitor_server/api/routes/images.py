"""Route handlers for the scheduled-timelapse gallery.

Endpoints: list, fetch, delete, bulk-delete, delete-all, and a zip export. There
is no image-label / positive-negative / candidate-review workflow — the scheduled
timelapse images are the only image record in the active design.
"""
from __future__ import annotations

import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from visit_monitor_server.api.auth import require_device_secret
from visit_monitor_server.api.schemas.images import (
    BulkDeleteImagesRequest,
    DeleteAllRequest,
    DeleteAllResponse,
    DeleteImageResponse,
    ImageInfo,
    ImageListResponse,
)
from visit_monitor_server.config import (
    ADAPTIVE_DECISION_LOG_PATH,
    IMAGE_DIR,
    METRICS_PATH,
)
from visit_monitor_server.services import get_controller
from visit_monitor_server.services.image_store import image_file

router = APIRouter(tags=["images"], dependencies=[Depends(require_device_secret)])


def _scheduled_images() -> list[Path]:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(
        (p for p in IMAGE_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


@router.get("/images", response_model=ImageListResponse)
def list_images(limit: int = Query(default=40, ge=1, le=200)) -> ImageListResponse:
    image_paths = _scheduled_images()
    images = [
        ImageInfo(
            filename=path.name,
            captured_at=datetime.fromtimestamp(path.stat().st_mtime)
            .astimezone()
            .isoformat(timespec="seconds"),
            size_bytes=path.stat().st_size,
            url=f"/images/{path.name}",
        )
        for path in image_paths[:limit]
    ]
    return ImageListResponse(
        image_dir=str(IMAGE_DIR),
        image_count=len(image_paths),
        total_size_bytes=sum(p.stat().st_size for p in image_paths),
        images=images,
    )


@router.get("/images/{filename}")
def get_image(filename: str, download: bool = Query(default=False)) -> FileResponse:
    path = image_file(filename)
    return FileResponse(
        path,
        media_type="image/jpeg",
        filename=path.name if download else None,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/exports/images.zip")
def download_images_archive() -> FileResponse:
    image_paths = sorted(_scheduled_images(), key=lambda p: p.stat().st_mtime)
    with tempfile.NamedTemporaryFile(
        prefix="pollipi_images_", suffix=".zip", dir=IMAGE_DIR.parent, delete=False
    ) as tmp:
        archive_path = Path(tmp.name)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in image_paths:
            archive.write(path, arcname=f"images/{path.name}")
        # Include the adaptive/shadow metadata logs so a session is self-contained.
        for log_path in (ADAPTIVE_DECISION_LOG_PATH, METRICS_PATH):
            if log_path.is_file():
                archive.write(log_path, arcname=f"logs/{log_path.name}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"pollipi_images_{timestamp}.zip",
        background=BackgroundTask(archive_path.unlink, missing_ok=True),
    )


@router.delete("/images/{filename}", response_model=DeleteImageResponse)
def delete_image(filename: str) -> DeleteImageResponse:
    path = image_file(filename)
    path.unlink()
    get_controller().clear_latest_if_deleted(path)
    return DeleteImageResponse(deleted=filename, message="Image deleted.")


@router.delete("/images", response_model=DeleteAllResponse)
def delete_all_images(request: DeleteAllRequest) -> DeleteAllResponse:
    if request.confirm != "DELETE_ALL":
        raise HTTPException(status_code=400, detail="Type DELETE_ALL to confirm deletion.")
    if get_controller().status().running:
        raise HTTPException(status_code=409, detail="Stop timelapse before deleting all images.")
    image_paths = _scheduled_images()
    for p in image_paths:
        p.unlink()
    get_controller().clear_latest_if_deleted()
    return DeleteAllResponse(deleted_count=len(image_paths), message="All images deleted.")


@router.post("/images/bulk-delete", response_model=DeleteAllResponse)
def bulk_delete_images(request: BulkDeleteImagesRequest) -> DeleteAllResponse:
    if not request.filenames:
        raise HTTPException(status_code=400, detail="No filenames specified.")
    deleted = 0
    for filename in request.filenames:
        try:
            path = image_file(filename)
            path.unlink()
            get_controller().clear_latest_if_deleted(path)
            deleted += 1
        except HTTPException:
            pass
    return DeleteAllResponse(deleted_count=deleted, message=f"{deleted} image(s) deleted.")
