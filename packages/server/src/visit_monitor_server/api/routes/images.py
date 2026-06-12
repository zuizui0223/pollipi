"""Route handlers for /images, /images/{filename}, /exports/images.zip."""
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
    LabelRequest,
    LabelResponse,
)
from visit_monitor_server.config import (
    EVENT_LOG_PATH,
    IMAGE_DIR,
    LABEL_LOG_PATH,
    LEGACY_CANDIDATE_DIR,
    METRICS_PATH,
    MODEL_INFO_PATH,
    NEGATIVE_DIR,
    OBSERVATION_LOG_PATH,
    POSITIVE_DIR,
)
from visit_monitor_server.services import get_controller
from visit_monitor_server.services.image_store import (
    collection_dir,
    image_file,
    label_index,
    register_label,
    remove_label,
    review_status,
)

router = APIRouter(tags=["images"], dependencies=[Depends(require_device_secret)])


@router.get("/images", response_model=ImageListResponse)
def list_images(
    limit: int = Query(default=40, ge=1, le=200),
    collection: str = Query(default="all"),
) -> ImageListResponse:
    if collection == "candidates":
        collection = "positive"
    image_dir = collection_dir(collection)
    image_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(
        (p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    idx = label_index()
    images = []
    for path in image_paths[:limit]:
        label_data = idx.get(path.name, {})
        lbl = label_data.get("label") or (collection if collection in {"positive", "negative"} else None)
        label_src = label_data.get("source")
        rev_status = review_status(label_src)
        auto_category = (
            lbl if lbl in {"positive", "negative"} and rev_status == "auto" else "unclear"
        )
        if collection in {"positive", "negative"} and not lbl:
            auto_category = collection
        final_category = lbl if lbl in {"positive", "negative"} else auto_category
        images.append(
            ImageInfo(
                filename=path.name,
                captured_at=datetime.fromtimestamp(path.stat().st_mtime)
                .astimezone()
                .isoformat(timespec="seconds"),
                size_bytes=path.stat().st_size,
                url=f"/images/{path.name}?collection={collection}",
                label=lbl,
                label_source=label_src,
                review_status=rev_status,
                auto_category=auto_category,
                final_category=final_category,
                category_source="manual" if rev_status == "reviewed" else "auto",
            )
        )
    return ImageListResponse(
        image_dir=str(image_dir),
        collection=collection,
        image_count=len(image_paths),
        total_size_bytes=sum(p.stat().st_size for p in image_paths),
        images=images,
    )


@router.get("/images/{filename}")
def get_image(
    filename: str,
    collection: str = Query(default="all"),
    download: bool = Query(default=False),
) -> FileResponse:
    path = image_file(filename, collection)
    return FileResponse(
        path,
        media_type="image/jpeg",
        filename=path.name if download else None,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/exports/images.zip")
def download_images_archive(collection: str = Query(default="all")) -> FileResponse:
    if collection == "candidates":
        collection = "positive"
    image_dir = collection_dir(collection)
    image_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(
        (p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}),
        key=lambda p: p.stat().st_mtime,
    )
    prefix = f"{collection}_images"
    with tempfile.NamedTemporaryFile(
        prefix=f"pollipi_{prefix}_",
        suffix=".zip",
        dir=IMAGE_DIR.parent,
        delete=False,
    ) as tmp:
        archive_path = Path(tmp.name)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in image_paths:
            archive.write(path, arcname=f"{prefix}/{path.name}")
        if collection == "all":
            for log_path in (OBSERVATION_LOG_PATH, METRICS_PATH, EVENT_LOG_PATH, LABEL_LOG_PATH, MODEL_INFO_PATH):
                if log_path.is_file():
                    archive.write(log_path, arcname=f"logs/{log_path.name}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"pollipi_{prefix}_{timestamp}.zip",
        background=BackgroundTask(archive_path.unlink, missing_ok=True),
    )


@router.post("/images/{filename}/label", response_model=LabelResponse)
def label_image(filename: str, request: LabelRequest) -> LabelResponse:
    original_path = image_file(filename, "all")
    controller = get_controller()
    if request.label == "unlabeled":
        remove_label(filename)
        return LabelResponse(
            filename=filename,
            label=request.label,
            label_source="manual_unlabeled",
            review_status="unlabeled",
            message="Image label removed.",
        )
    if request.label == "confirmed":
        idx = label_index()
        current_label = idx.get(filename, {}).get("label")
        if current_label not in {"positive", "negative"}:
            if (POSITIVE_DIR / filename).is_file():
                current_label = "positive"
            elif (NEGATIVE_DIR / filename).is_file():
                current_label = "negative"
        if current_label not in {"positive", "negative"}:
            raise HTTPException(status_code=400, detail="Image has no positive/negative label to confirm.")
        register_label(original_path, current_label, "manual_confirmed")
        return LabelResponse(
            filename=filename,
            label=current_label,
            label_source="manual_confirmed",
            review_status="reviewed",
            message="Auto label confirmed by reviewer.",
        )
    if request.label not in {"positive", "negative"}:
        raise HTTPException(
            status_code=400,
            detail="Label must be positive, negative, confirmed, or unlabeled.",
        )
    register_label(original_path, request.label, "manual_ipad_review")
    return LabelResponse(
        filename=filename,
        label=request.label,
        label_source="manual_ipad_review",
        review_status="reviewed",
        message="Reviewed image label saved.",
    )


@router.delete("/images/{filename}", response_model=DeleteImageResponse)
def delete_image(filename: str) -> DeleteImageResponse:
    path = image_file(filename)
    remove_label(path.name)
    path.unlink()
    get_controller().clear_latest_if_deleted(path)
    return DeleteImageResponse(deleted=filename, message="Image deleted.")


@router.delete("/images", response_model=DeleteAllResponse)
def delete_all_images(request: DeleteAllRequest) -> DeleteAllResponse:
    if request.confirm != "DELETE_ALL":
        raise HTTPException(status_code=400, detail="Type DELETE_ALL to confirm deletion.")
    if get_controller().status().running:
        raise HTTPException(status_code=409, detail="Stop timelapse before deleting all images.")
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    image_paths = [
        p for p in IMAGE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}
    ]
    for p in image_paths:
        p.unlink()
    for directory in (POSITIVE_DIR, NEGATIVE_DIR, LEGACY_CANDIDATE_DIR):
        if directory.is_dir():
            for p in directory.iterdir():
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}:
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
            path = image_file(filename, "all")
            remove_label(path.name)
            path.unlink()
            get_controller().clear_latest_if_deleted(path)
            deleted += 1
        except HTTPException:
            pass
    return DeleteAllResponse(deleted_count=deleted, message=f"{deleted} image(s) deleted.")
