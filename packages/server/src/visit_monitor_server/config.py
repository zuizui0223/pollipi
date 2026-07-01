"""Global configuration constants for PolliPi visit-monitor server.

All paths and device metadata are resolved once at import time from
environment variables so the rest of the codebase can import them
without worrying about env-var plumbing.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
from pathlib import Path
from typing import Optional


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


# ---------------------------------------------------------------------------
# Storage layout
# ---------------------------------------------------------------------------
# The image directory is the ONLY path that can be redirected at runtime (for
# example onto an external USB drive) through the /storage API. Everything else
# — the policy artifact, the autonomous-run flag, and the persisted storage
# choice itself — is anchored to BASE_DIR on the SD card so device-local state
# survives an unplugged, swapped, or unwritable external drive.
_DEFAULT_IMAGE_DIR = Path(
    os.getenv("POLLIPI_IMAGE_DIR", str(Path.home() / "pollipi_timelapse" / "images"))
).expanduser()

BASE_DIR = _DEFAULT_IMAGE_DIR.parent
STORAGE_CONFIG_PATH = BASE_DIR / "storage_config.json"

METRICS_FILENAME = "adaptive_metrics.csv"
ADAPTIVE_DECISION_LOG_FILENAME = "adaptive_decisions.csv"


def _load_persisted_image_dir() -> Optional[Path]:
    """Return the web-selected image dir from storage_config.json, if any."""
    try:
        data = json.loads(STORAGE_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    raw = data.get("image_dir") if isinstance(data, dict) else None
    if not raw:
        return None
    return Path(str(raw)).expanduser()


# Runtime-mutable active image directory. A persisted web choice wins over the
# env-var/default so the last /storage selection survives a restart; clearing
# the persisted file (or selecting the default) falls back to the env var or the
# built-in default.
_active_image_dir: Path = _load_persisted_image_dir() or _DEFAULT_IMAGE_DIR


def get_default_image_dir() -> Path:
    """The SD-card image directory from the env var / built-in default."""
    return _DEFAULT_IMAGE_DIR


def get_image_dir() -> Path:
    """The active image directory (may point at external storage)."""
    return _active_image_dir


def get_metrics_path() -> Path:
    return _active_image_dir / METRICS_FILENAME


def get_adaptive_decision_log_path() -> Path:
    return _active_image_dir / ADAPTIVE_DECISION_LOG_FILENAME


def set_image_dir(path: Path, *, persist: bool = True) -> Path:
    """Point the active image directory at *path* and optionally persist it.

    Callers must validate writability and ensure capture is stopped before
    switching; this only updates process state and the on-disk
    ``storage_config.json`` used to restore the choice after a restart. Selecting
    the default clears the persisted override.
    """
    global _active_image_dir
    resolved = Path(path).expanduser()
    _active_image_dir = resolved
    if persist:
        try:
            STORAGE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            if resolved == _DEFAULT_IMAGE_DIR:
                STORAGE_CONFIG_PATH.unlink(missing_ok=True)
            else:
                STORAGE_CONFIG_PATH.write_text(
                    json.dumps({"image_dir": str(resolved)}, ensure_ascii=False),
                    encoding="utf-8",
                )
        except OSError:
            # Persistence is best-effort; the in-process switch still applies.
            pass
    return _active_image_dir


AUTONOMOUS_PATH = BASE_DIR / "autonomous_run.json"

# Issue #27 probe-only three-stage shadow: low-resolution probes run every
# PROBE_INTERVAL_SEC (no JPEG saved); high-resolution JPEGs stay on the fixed
# scheduled interval. Live adaptive capture timing remains disabled.
PROBE_INTERVAL_SEC = float(os.getenv("POLLIPI_PROBE_INTERVAL_SEC", "5"))
LIVE_ADAPTIVE_ENABLED = env_bool("POLLIPI_LIVE_ADAPTIVE_ENABLED", False)

# Versioned mesh policy artifact loaded at startup (Issue #21). When present the
# Pi builds its analysis configuration from this JSON; otherwise a built-in
# baseline rule config is used. The Pi never runs the simulation/search itself.
# The official artifact is the Mode-3 runtime-bridge export
# (mode3_runtime_bridge_policy_v1.json); the legacy pairwise search writes a
# separate legacy_pairwise_policy.json that the Pi does NOT load.
POLICY_PATH = Path(
    os.getenv("POLLIPI_POLICY_PATH", str(BASE_DIR / "mode3_runtime_bridge_policy_v1.json"))
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
# Main stream size for the video configuration used by HIGH=video runs (1080p).
VIDEO_SIZE = (1920, 1080)

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
