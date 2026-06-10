"""Global configuration constants for PolliPi visit-monitor server.

All paths and device metadata are resolved once at import time from
environment variables so the rest of the codebase can import them
without worrying about env-var plumbing.
"""
from __future__ import annotations

import os
import socket
from pathlib import Path


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


# ---------------------------------------------------------------------------
# Storage layout
# ---------------------------------------------------------------------------
IMAGE_DIR = Path(
    os.getenv("POLLIPI_IMAGE_DIR", str(Path.home() / "pollipi_timelapse" / "images"))
).expanduser()

METRICS_PATH = IMAGE_DIR / "adaptive_metrics.csv"
OBSERVATION_LOG_PATH = IMAGE_DIR / "observation_events.csv"
EVENT_LOG_PATH = IMAGE_DIR / "event_log.csv"
LABEL_LOG_PATH = IMAGE_DIR / "image_labels.csv"
POSITIVE_DIR = IMAGE_DIR / "positive"
NEGATIVE_DIR = IMAGE_DIR / "negative"
LEGACY_CANDIDATE_DIR = IMAGE_DIR / "candidates"
MODEL_DIR = IMAGE_DIR.parent / "models"
MODEL_PATH = MODEL_DIR / "insect_presence_svm.xml"
MODEL_INFO_PATH = MODEL_DIR / "insect_presence_model.json"
AUTONOMOUS_PATH = IMAGE_DIR.parent / "autonomous_run.json"

WEB_DIR = Path(__file__).parent.parent.parent.parent.parent / "web"
PREVIEW_PATH = Path("/tmp/pollipi_preview.jpg")

# ---------------------------------------------------------------------------
# Camera / device identity
# ---------------------------------------------------------------------------
DEVICE_ID = os.getenv("POLLIPI_DEVICE_ID", socket.gethostname())
DEVICE_NAME = os.getenv("POLLIPI_DEVICE_NAME", socket.gethostname())
CAMERA_LABEL = os.getenv("POLLIPI_CAMERA_LABEL", "PolliPi Camera")
CAMERA_MODEL = os.getenv("POLLIPI_CAMERA_MODEL", "Picamera2 camera")
CAMERA_PROFILE = os.getenv("POLLIPI_CAMERA_PROFILE", "unspecified")
IS_AI_CAMERA = env_bool("POLLIPI_IS_AI_CAMERA")
IS_NOIR = env_bool("POLLIPI_IS_NOIR")
IS_WIDE = env_bool("POLLIPI_IS_WIDE")
USE_FAKE_CAMERA = env_bool("POLLIPI_FAKE_CAMERA")

# ---------------------------------------------------------------------------
# Monitor / vision
# ---------------------------------------------------------------------------
MONITOR_SIZE = (640, 360)
MONITOR_FRAME_INTERVAL_SEC = 0.25

FLOWER_ROI_MODEL = os.getenv("POLLIPI_FLOWER_ROI_MODEL", "")

AI_MONITOR_MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
AI_MONITOR_THRESHOLD = 0.55
AI_MONITOR_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "-", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "-", "backpack",
    "umbrella", "-", "-", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "-", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
    "donut", "cake", "chair", "couch", "potted plant", "bed", "-", "dining table", "-",
    "-", "toilet", "-", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "-", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]

# ---------------------------------------------------------------------------
# Event / label metadata
# ---------------------------------------------------------------------------
FALSE_POSITIVE_REASONS = {
    "",
    "wind",
    "shadow",
    "flower_movement",
    "camera_shake",
    "non_insect_object",
    "lighting_change",
    "unclear",
    "other",
}

EVENT_LOG_COLUMNS = [
    "event_id", "timestamp", "image_filename",
    "device_id", "device_name", "camera_label", "camera_model", "camera_profile",
    "is_ai_camera", "is_noir", "is_wide",
    "site_id", "flower_id", "plant_species", "observer", "notes",
    "comparison_session_id", "camera_role", "method_mode",
    "motion_score", "changed_area_ratio", "mean_brightness", "brightness_delta",
    "wind_like_motion", "num_blobs", "largest_blob_area", "largest_blob_ratio",
    "small_blob_count", "motion_type", "roi_used", "roi_x", "roi_y", "roi_w", "roi_h",
    "roi_tracking", "roi_tracking_success", "roi_tracking_score", "roi_search_margin",
    "roi_tracking_min_score", "initial_roi_x", "initial_roi_y", "initial_roi_w", "initial_roi_h",
    "tracked_roi_x", "tracked_roi_y", "tracked_roi_w", "tracked_roi_h", "roi_shift_x", "roi_shift_y",
    "manual_label", "manual_taxon", "false_positive_reason", "manual_notes", "reviewed_at",
]

DERIVED_EVENT_COLUMNS = {
    "auto_category",
    "final_category",
    "category_source",
    "review_status",
    "final_label",
}
