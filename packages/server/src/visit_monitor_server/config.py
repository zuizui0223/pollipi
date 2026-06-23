"""Global configuration constants for PolliPi visit-monitor server.

All paths and device metadata are resolved once at import time from
environment variables so the rest of the codebase can import them
without worrying about env-var plumbing.
"""
from __future__ import annotations

import os
import socket
import tempfile
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
ADAPTIVE_DECISION_LOG_PATH = IMAGE_DIR / "adaptive_decisions.csv"
AUTONOMOUS_PATH = IMAGE_DIR.parent / "autonomous_run.json"

# Versioned mesh policy artifact loaded at startup (Issue #21). When present the
# Pi builds its analysis configuration from this JSON; otherwise a built-in
# baseline rule config is used. The Pi never runs the simulation/search itself.
POLICY_PATH = Path(
    os.getenv("POLLIPI_POLICY_PATH", str(IMAGE_DIR.parent / "simulation_informed_policy.json"))
).expanduser()

WEB_DIR = Path(
    os.getenv("POLLIPI_WEB_DIR", str(Path.home() / "pollipi_timelapse" / "web"))
).expanduser()
PREVIEW_PATH = Path(
    os.getenv("POLLIPI_PREVIEW_PATH", str(Path(tempfile.gettempdir()) / "pollipi_preview.jpg"))
).expanduser()

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
DEVICE_SECRET = os.getenv("POLLIPI_DEVICE_SECRET", "").strip()
ENABLE_LEGACY_ROUTES = env_bool("POLLIPI_ENABLE_LEGACY_ROUTES")

# ---------------------------------------------------------------------------
# Monitor / vision
# ---------------------------------------------------------------------------
MONITOR_SIZE = (640, 360)
MONITOR_FRAME_INTERVAL_SEC = 0.25

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
