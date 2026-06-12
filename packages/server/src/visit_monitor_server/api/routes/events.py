"""Route handlers for /events."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from visit_monitor_server.api.auth import require_device_secret
from visit_monitor_server.api.schemas.events import (
    BulkDeleteEventsRequest,
    EventLabelRequest,
    EventLabelResponse,
    EventListResponse,
)
from visit_monitor_server.api.schemas.images import DeleteAllResponse
from visit_monitor_server.config import FALSE_POSITIVE_REASONS, IMAGE_DIR
from visit_monitor_server.services import get_controller
from visit_monitor_server.services.event_log import read_event_rows, write_event_rows
from visit_monitor_server.services.image_store import remove_label

router = APIRouter(tags=["events"], dependencies=[Depends(require_device_secret)])


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


@router.post("/events/bulk-delete", response_model=DeleteAllResponse)
def bulk_delete_events(request: BulkDeleteEventsRequest) -> DeleteAllResponse:
    if request.scope not in {"event_only", "event_and_images", "event_images_labels"}:
        raise HTTPException(status_code=400, detail="scope must be event_only, event_and_images, or event_images_labels.")
    if not request.event_ids:
        raise HTTPException(status_code=400, detail="No event_ids specified.")
    rows = read_event_rows()
    id_set = set(request.event_ids)
    to_delete = [row for row in rows if row.get("event_id") in id_set]
    remaining = [row for row in rows if row.get("event_id") not in id_set]
    if request.scope in {"event_and_images", "event_images_labels"}:
        for row in to_delete:
            filename = row.get("image_filename", "")
            if filename:
                path = IMAGE_DIR / filename
                if path.is_file():
                    if request.scope == "event_images_labels":
                        remove_label(filename)
                    path.unlink(missing_ok=True)
                    get_controller().clear_latest_if_deleted(path)
    write_event_rows(remaining)
    return DeleteAllResponse(deleted_count=len(to_delete), message=f"{len(to_delete)} event(s) deleted.")
