"""Route handlers for the image-storage location (SD card vs external USB).

``GET /storage`` reports the active directory plus detected candidates (SD
default, current selection, and mounts under /media and /mnt) with free space.
``POST /storage`` switches where new photos and adaptive logs are written. The
switch is only allowed while capture is stopped, so no in-flight loop is ever
redirected mid-write.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from visit_monitor_server.adapters.storage_info import discover_targets
from visit_monitor_server.api.auth import require_device_secret
from visit_monitor_server.api.schemas.storage import (
    SetStorageRequest,
    StorageInfoResponse,
    StorageTarget,
)
from visit_monitor_server.config import (
    get_default_image_dir,
    get_image_dir,
    set_image_dir,
)
from visit_monitor_server.services import get_controller

router = APIRouter(tags=["storage"])


def _storage_info() -> StorageInfoResponse:
    current = get_image_dir()
    default = get_default_image_dir()
    return StorageInfoResponse(
        current_path=str(current),
        default_path=str(default),
        capture_running=get_controller().status().running,
        targets=[StorageTarget(**t) for t in discover_targets(current, default)],
    )


@router.get("/storage", response_model=StorageInfoResponse)
def get_storage() -> StorageInfoResponse:
    return _storage_info()


@router.post(
    "/storage",
    response_model=StorageInfoResponse,
    dependencies=[Depends(require_device_secret)],
)
def set_storage(request: SetStorageRequest) -> StorageInfoResponse:
    controller = get_controller()
    if controller.status().running:
        raise HTTPException(
            status_code=409,
            detail="Stop capture before changing the storage location.",
        )

    raw = (request.path or "").strip()
    if not raw:
        new_dir = get_default_image_dir()
    else:
        new_dir = Path(raw).expanduser()
        if not new_dir.is_absolute():
            raise HTTPException(status_code=422, detail="Storage path must be absolute.")

    # Verify the target is actually writable before committing. A read-only mount
    # or a systemd sandbox that does not list the mount in ReadWritePaths surfaces
    # here as a clear error instead of silently failing at the first capture.
    try:
        new_dir.mkdir(parents=True, exist_ok=True)
        probe = new_dir / ".pollipi_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Storage path is not writable ({exc}). Ensure the drive is "
                "mounted and that the pollipi service may write there "
                "(systemd ReadWritePaths must include the mount)."
            ),
        ) from exc

    try:
        controller.set_image_dir(new_dir)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    set_image_dir(new_dir)
    return _storage_info()
