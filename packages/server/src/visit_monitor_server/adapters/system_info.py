"""System information helpers (disk usage, vcgencmd throttle status)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional


def disk_usage(path: Path) -> dict:
    """Return a dict with storage stats for *path*."""
    path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(path)
    return {
        "storage_path": str(path),
        "storage_total_bytes": usage.total,
        "storage_used_bytes": usage.used,
        "storage_free_bytes": usage.free,
        "storage_percent_used": round(usage.used / usage.total * 100, 1) if usage.total else 0.0,
    }


def throttle_status() -> dict:
    """
    Query ``vcgencmd get_throttled`` and return parsed flags.

    Returns a dict with keys:
    - ``throttled_raw``: raw output string (or ``None`` if unavailable)
    - ``undervoltage_now``: bool or None
    - ``undervoltage_occurred``: bool or None
    - ``power_message``: human-readable summary
    """
    throttled_raw: Optional[str] = None
    undervoltage_now: Optional[bool] = None
    undervoltage_occurred: Optional[bool] = None
    power_message = "Battery percentage is unavailable without a telemetry-capable power source."

    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        throttled_raw = result.stdout.strip()
        flags = int(throttled_raw.split("=")[-1], 16)
        undervoltage_now = bool(flags & 0x1)
        undervoltage_occurred = bool(flags & 0x10000)
        if undervoltage_now:
            power_message = "Undervoltage detected now; check battery output and cable."
        elif undervoltage_occurred:
            power_message = "Undervoltage occurred since boot; check battery output and cable."
        else:
            power_message = "Voltage OK; battery percentage requires telemetry hardware."
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        pass

    return {
        "throttled_raw": throttled_raw,
        "undervoltage_now": undervoltage_now,
        "undervoltage_occurred": undervoltage_occurred,
        "power_message": power_message,
    }
