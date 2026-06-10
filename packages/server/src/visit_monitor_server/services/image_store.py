"""Image-store helpers: directory resolution, file lookup, label management."""
from __future__ import annotations

import csv
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from visit_monitor_server.config import (
    IMAGE_DIR,
    LABEL_LOG_PATH,
    LEGACY_CANDIDATE_DIR,
    NEGATIVE_DIR,
    POSITIVE_DIR,
)


# ---------------------------------------------------------------------------
# Directory / file resolution
# ---------------------------------------------------------------------------

def collection_dir(collection: str) -> Path:
    """Return the filesystem directory for *collection*.

    Raises ``HTTPException(400)`` for unknown collection names.
    """
    if collection == "candidates":
        collection = "positive"
    directories = {"all": IMAGE_DIR, "positive": POSITIVE_DIR, "negative": NEGATIVE_DIR}
    if collection not in directories:
        raise HTTPException(status_code=400, detail="Invalid image collection.")
    return directories[collection]


def image_file(filename: str, collection: str = "all") -> Path:
    """Validate *filename* and return its absolute path.

    Raises ``HTTPException(400)`` for unsafe filenames and ``HTTPException(404)``
    if the file does not exist.
    """
    if Path(filename).name != filename or Path(filename).suffix.lower() not in {".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Invalid image filename.")
    path = collection_dir(collection) / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return path


# ---------------------------------------------------------------------------
# Label index
# ---------------------------------------------------------------------------

def label_index() -> dict[str, dict[str, str]]:
    """Read ``image_labels.csv`` and return a ``{filename: {label, source}}`` dict."""
    labels: dict[str, dict[str, str]] = {}
    if not LABEL_LOG_PATH.is_file():
        return labels
    try:
        with LABEL_LOG_PATH.open("r", newline="", encoding="utf-8") as csv_file:
            for row in csv.DictReader(csv_file):
                filename = row.get("image_filename", "")
                lbl = row.get("label", "")
                src = row.get("source", "")
                if filename:
                    labels[filename] = {"label": lbl, "source": src}
    except OSError:
        pass
    return labels


def review_status(source: Optional[str]) -> str:
    """Map label *source* to a human-readable review-status string."""
    if source in {"manual_ipad_review", "manual_confirmed"}:
        return "reviewed"
    if source:
        return "auto"
    return "unlabeled"


# ---------------------------------------------------------------------------
# Label registration
# ---------------------------------------------------------------------------

def register_label(image_path: Path, label: str, source: str) -> None:
    """Hard-link (or copy) *image_path* into the positive/negative sub-directory
    and append an entry to ``image_labels.csv``."""
    if label not in {"positive", "negative"}:
        raise ValueError("Invalid image label.")
    target_dir = POSITIVE_DIR if label == "positive" else NEGATIVE_DIR
    other_dir = NEGATIVE_DIR if label == "positive" else POSITIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    other_dir.mkdir(parents=True, exist_ok=True)
    other_path = other_dir / image_path.name
    if other_path.is_file():
        other_path.unlink()
    target_path = target_dir / image_path.name
    if not target_path.exists():
        try:
            os.link(image_path, target_path)
        except OSError:
            shutil.copy2(image_path, target_path)
    write_header = not LABEL_LOG_PATH.exists()
    with LABEL_LOG_PATH.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if write_header:
            writer.writerow(["timestamp", "image_filename", "label", "source"])
        writer.writerow([
            datetime.now().astimezone().isoformat(timespec="seconds"),
            image_path.name,
            label,
            source,
        ])


def remove_label(filename: str) -> None:
    """Remove hard-links for *filename* from all label directories."""
    for directory in (POSITIVE_DIR, NEGATIVE_DIR, LEGACY_CANDIDATE_DIR):
        path = directory / filename
        if path.is_file():
            path.unlink()
