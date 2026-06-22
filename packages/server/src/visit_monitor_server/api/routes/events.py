"""Route handlers for /events."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from visit_monitor_server.api.auth import require_device_secret
from visit_monitor_server.api.schemas.events import (
    BulkDeleteEventsRequest,
    BulkDeleteEventsResponse,
    BulkDeleteEventFailure,
    EventLabelRequest,
    EventLabelResponse,
    EventListResponse,
)
from visit_monitor_server.config import FALSE_POSITIVE_REASONS, IMAGE_DIR, OBSERVATION_LOG_PATH
from visit_monitor_server.services import get_controller
from visit_monitor_server.services.event_log import read_event_rows, write_event_rows

router = APIRouter(tags=["events"], dependencies=[Depends(require_device_secret)])

EVENT_DELETE_SCOPES = {"event_only", "event_and_event_image"}
BASELINE_CAPTURE_TYPES = {"scheduled", "scheduled_event", "baseline", "timelapse", "scheduled_timelapse"}
EVENT_IMAGE_CAPTURE_TYPES = {"event"}


def _image_capture_types() -> dict[str, set[str]]:
    if not OBSERVATION_LOG_PATH.is_file():
        return {}
    capture_types: dict[str, set[str]] = {}
    with OBSERVATION_LOG_PATH.open("r", newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            capture_type = row.get("capture_type", "").strip().lower()
            filename = row.get("image_filename", "").strip()
            if filename:
                capture_types.setdefault(filename, set()).add(capture_type or "unknown")
    return capture_types


def _event_image_delete_reason(filename: str, capture_types: dict[str, set[str]]) -> str | None:
    if not OBSERVATION_LOG_PATH.is_file():
        return "observation log missing; image provenance is unknown"
    types = capture_types.get(filename)
    if not types:
        return "image is not present in observation log; image provenance is unknown"
    if types & BASELINE_CAPTURE_TYPES:
        return "image belongs to scheduled/baseline capture; image was not deleted"
    if types != EVENT_IMAGE_CAPTURE_TYPES:
        return f"image is not proven event-only; capture_type={','.join(sorted(types))}"
    return None


def _resolve_event_image(filename: str) -> tuple[Path | None, str | None]:
    clean = Path(filename).name
    if not clean or clean != filename:
        return None, "unsafe image filename"
    if Path(clean).suffix.lower() not in {".jpg", ".jpeg"}:
        return None, "event image is not a JPEG"
    path = (IMAGE_DIR / clean).resolve()
    image_root = IMAGE_DIR.resolve()
    if path.parent != image_root:
        return None, "event image is outside image directory"
    return path, None


@router.get("/events", response_model=EventListResponse)
def list_events(
    limit: int = Query(default=50, ge=1, le=500),
    label: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    site_id: Optional[str] = Query(default=None),
    flower_id: Optional[str] = Query(default=None),
    comparison_session_id: Optional[str] = Query(default=None),
) -> EventListResponse:
    rows = read_event_rows()
    if label is not None:
        rows = [row for row in rows if row.get("manual_label") == label]
    if category is not None:
        if category not in {"positive", "negative", "unclear", "all"}:
            raise HTTPException(status_code=400, detail="category must be positive, negative, unclear, or all.")
        if category != "all":
            rows = [row for row in rows if row.get("final_category") == category]
    if site_id is not None:
        rows = [row for row in rows if row.get("site_id") == site_id]
    if flower_id is not None:
        rows = [row for row in rows if row.get("flower_id") == flower_id]
    if comparison_session_id is not None:
        rows = [row for row in rows if row.get("comparison_session_id") == comparison_session_id]
    rows = rows[-limit:]
    rows.reverse()
    return EventListResponse(event_count=len(rows), events=rows)


@router.post("/events/{event_id}/label", response_model=EventLabelResponse)
def label_event(event_id: str, request: EventLabelRequest) -> EventLabelResponse:
    false_positive_reason = (request.false_positive_reason or "").strip()
    if false_positive_reason not in FALSE_POSITIVE_REASONS:
        raise HTTPException(status_code=400, detail="Invalid false_positive_reason.")
    rows = read_event_rows()
    for row in rows:
        if row.get("event_id") == event_id:
            if request.manual_label is not None:
                manual_label = request.manual_label.strip()
                if manual_label not in {"insect", "non_insect", "unclear"}:
                    raise HTTPException(
                        status_code=400,
                        detail="manual_label must be insect, non_insect, or unclear.",
                    )
                row["manual_label"] = manual_label
                if manual_label == "insect":
                    false_positive_reason = ""
            if request.manual_taxon is not None:
                row["manual_taxon"] = request.manual_taxon.strip()
            if request.false_positive_reason is not None:
                row["false_positive_reason"] = false_positive_reason
            if request.manual_notes is not None:
                row["manual_notes"] = request.manual_notes.strip()
            row["reviewed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            write_event_rows(rows)
            return EventLabelResponse(
                event_id=event_id,
                manual_label=row.get("manual_label", ""),
                manual_taxon=row.get("manual_taxon", ""),
                false_positive_reason=row.get("false_positive_reason", ""),
                manual_notes=row.get("manual_notes", ""),
                reviewed_at=row.get("reviewed_at", ""),
                message="Event review label saved.",
            )
    raise HTTPException(status_code=404, detail="Event not found.")


@router.get("/events/export_labels.csv")
def export_event_labels() -> Response:
    rows = [row for row in read_event_rows() if row.get("manual_label")]
    output = io.StringIO()
    fieldnames = [
        "event_id", "timestamp", "image_filename",
        "auto_category", "manual_label", "final_label", "final_category", "category_source", "review_status",
        "manual_taxon", "false_positive_reason", "manual_notes",
        "device_id", "device_name", "camera_label", "camera_model", "camera_profile",
        "site_id", "flower_id", "plant_species", "observer", "comparison_session_id", "camera_role", "method_mode",
        "motion_score", "changed_area_ratio", "brightness_delta", "motion_type",
        "roi_used", "roi_x", "roi_y", "roi_w", "roi_h", "reviewed_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=event_labels.csv"},
    )


@router.post("/events/bulk-delete", response_model=BulkDeleteEventsResponse)
def bulk_delete_events(request: BulkDeleteEventsRequest) -> BulkDeleteEventsResponse:
    if request.scope not in EVENT_DELETE_SCOPES:
        raise HTTPException(status_code=400, detail="scope must be event_only or event_and_event_image.")
    if not request.event_ids:
        raise HTTPException(status_code=400, detail="No event_ids specified.")
    rows = read_event_rows()
    id_set = {event_id.strip() for event_id in request.event_ids if event_id.strip()}
    if not id_set:
        raise HTTPException(status_code=400, detail="No event_ids specified.")
    row_by_id = {row.get("event_id", ""): row for row in rows}
    failures: list[BulkDeleteEventFailure] = []
    for event_id in sorted(id_set):
        if event_id not in row_by_id:
            failures.append(BulkDeleteEventFailure(event_id=event_id, reason="event not found"))
    to_delete = [row for row in rows if row.get("event_id") in id_set]
    remaining = [row for row in rows if row.get("event_id") not in id_set]
    image_deleted_count = 0
    if request.scope == "event_and_event_image":
        capture_types = _image_capture_types()
        for row in to_delete:
            event_id = row.get("event_id", "")
            filename = row.get("image_filename", "")
            if not filename:
                failures.append(BulkDeleteEventFailure(
                    event_id=event_id,
                    reason="event has no image filename; image was not deleted",
                ))
                continue
            provenance_reason = _event_image_delete_reason(filename, capture_types)
            if provenance_reason:
                failures.append(BulkDeleteEventFailure(
                    event_id=event_id,
                    reason=provenance_reason,
                ))
                continue
            path, reason = _resolve_event_image(filename)
            if reason or path is None:
                failures.append(BulkDeleteEventFailure(event_id=event_id, reason=reason or "invalid image"))
                continue
            if path.is_file():
                path.unlink(missing_ok=True)
                image_deleted_count += 1
                get_controller().clear_latest_if_deleted(path)
    write_event_rows(remaining)
    message = f"{len(to_delete)} event(s) deleted."
    if image_deleted_count:
        message += f" {image_deleted_count} event image(s) deleted."
    if failures:
        message += f" {len(failures)} item(s) need attention."
    return BulkDeleteEventsResponse(
        deleted_count=len(to_delete),
        image_deleted_count=image_deleted_count,
        failed=failures,
        message=message,
    )
