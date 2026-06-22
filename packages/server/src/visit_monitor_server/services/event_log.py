"""Event log helpers: read, write, categorise."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from visit_monitor_server.config import (
    DERIVED_EVENT_COLUMNS,
    EVENT_LOG_COLUMNS,
    EVENT_LOG_PATH,
)


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------

def read_event_rows() -> list[dict[str, str]]:
    """Read ``event_log.csv`` and return a list of enriched row dicts."""
    if not EVENT_LOG_PATH.is_file():
        return []
    with EVENT_LOG_PATH.open("r", newline="", encoding="utf-8") as csv_file:
        rows = [dict(row) for row in csv.DictReader(csv_file)]
    for i, row in enumerate(rows):
        for column in EVENT_LOG_COLUMNS:
            row.setdefault(column, "")
        if not row.get("event_id"):
            ts = row.get("timestamp", "").replace(":", "").replace(" ", "_")
            fname = row.get("image_filename", "")
            row["event_id"] = f"fallback-{ts}-{fname}-{i}" if (ts or fname) else f"fallback-{i}"
        filename = row.get("image_filename", "")
        row["image_url"] = f"/images/{filename}" if filename else ""
        add_event_categories(row)
    return rows


def write_event_rows(rows: list[dict[str, str]]) -> None:
    """Overwrite ``event_log.csv`` with *rows*."""
    EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    extra_columns: list[str] = []
    for row in rows:
        for key in row:
            if (
                key not in EVENT_LOG_COLUMNS
                and key != "image_url"
                and key not in DERIVED_EVENT_COLUMNS
                and key not in extra_columns
            ):
                extra_columns.append(key)
    fieldnames = EVENT_LOG_COLUMNS + extra_columns
    with EVENT_LOG_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            cleaned = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(cleaned)


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------

def _row_float(row: dict[str, str], key: str) -> Optional[float]:
    value = row.get(key, "")
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_bool(row: dict[str, str], key: str) -> bool:
    return str(row.get(key, "")).strip().lower() in {"1", "true", "yes", "y", "on"}


def auto_event_category(row: dict[str, str]) -> str:
    """Derive a predicted category (positive/negative/unclear) from motion metrics."""
    motion_score = _row_float(row, "motion_score")
    changed_area_ratio = _row_float(row, "changed_area_ratio")
    largest_blob_ratio = _row_float(row, "largest_blob_ratio")
    small_blob_count = _row_float(row, "small_blob_count")
    brightness_delta = _row_float(row, "brightness_delta")
    detection_count = _row_float(row, "detection_count")
    wind_like = _row_bool(row, "wind_like_motion")
    insect_candidate = _row_bool(row, "insect_candidate")
    motion_type = row.get("motion_type", "")

    if insect_candidate or (detection_count is not None and detection_count > 0):
        return "positive" if not wind_like else "unclear"
    if wind_like or motion_type == "wind_like_large_motion":
        return "negative"
    if motion_type == "global_brightness_change":
        return "negative"
    if brightness_delta is not None and brightness_delta >= 35 and (changed_area_ratio or 0) < 0.01:
        return "negative"
    if motion_score is None and changed_area_ratio is None:
        return "unclear"
    score = max(motion_score or 0.0, changed_area_ratio or 0.0)
    if score < 0.001:
        return "negative"
    if score >= 0.01 and not wind_like:
        if largest_blob_ratio is not None and largest_blob_ratio >= 0.35:
            return "unclear"
        if small_blob_count is None or small_blob_count >= 1:
            return "positive"
    if 0.003 <= score < 0.01 and not wind_like:
        return "unclear"
    return "unclear"


def add_event_categories(row: dict[str, str]) -> dict[str, str]:
    """Enrich *row* in-place with derived category fields and return it."""
    manual_label = canonical_review_label(row.get("review_label") or row.get("manual_label", ""))
    if manual_label:
        row["review_label"] = manual_label
        row["manual_label"] = manual_label
    auto_category = auto_event_category(row)
    manual_map = {"visit": "positive", "noise": "negative", "unclear": "unclear"}
    final_category = manual_map.get(manual_label, auto_category)
    category_source = "manual" if manual_label else "auto"
    row["auto_category"] = auto_category
    row["final_category"] = final_category
    row["category_source"] = category_source
    row["review_status"] = "reviewed" if manual_label else "motion_candidate"
    row["final_label"] = final_category
    return row


def canonical_review_label(value: str | None) -> str:
    label = (value or "").strip()
    return {
        "insect": "visit",
        "positive": "visit",
        "visit": "visit",
        "non_insect": "noise",
        "negative": "noise",
        "noise": "noise",
        "unclear": "unclear",
    }.get(label, "")
