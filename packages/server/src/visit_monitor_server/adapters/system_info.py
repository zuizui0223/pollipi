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


def supply_voltage_v() -> Optional[float]:
    """Return the Pi 5 input 5V-rail voltage (``EXT5V_V``) from the PMIC, or None.

    A plain USB power bank exposes no state-of-charge, but on a Pi 5 the PMIC
    reports the actual input rail voltage. As a battery drains its output sags
    toward the undervoltage threshold (~4.6-4.8V), so this reading is the best
    available proxy for "battery health" when no fuel-gauge HAT is present.
    Older Pis without ``pmic_read_adc`` (or non-Pi hosts) return None.
    """
    try:
        result = subprocess.run(
            ["vcgencmd", "pmic_read_adc"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    # lines look like: "     EXT5V_V volt(24)=5.06386000V"
    for line in result.stdout.splitlines():
        if "EXT5V_V" in line and "=" in line:
            try:
                return round(float(line.split("=")[-1].strip().rstrip("V")), 3)
            except ValueError:
                return None
    return None


def throttle_status() -> dict:
    """
    Query ``vcgencmd get_throttled`` (+ PMIC input voltage) and return parsed flags.

    Returns a dict with keys:
    - ``throttled_raw``: raw output string (or ``None`` if unavailable)
    - ``undervoltage_now``: bool or None
    - ``undervoltage_occurred``: bool or None
    - ``supply_voltage_v``: float input 5V-rail voltage, or None (battery proxy)
    - ``power_message``: human-readable summary
    """
    throttled_raw: Optional[str] = None
    undervoltage_now: Optional[bool] = None
    undervoltage_occurred: Optional[bool] = None
    voltage = supply_voltage_v()
    volt_txt = f" ({voltage:.2f}V in)" if voltage is not None else ""
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
            power_message = f"Undervoltage detected now{volt_txt}; check battery output and cable."
        elif undervoltage_occurred:
            power_message = f"Undervoltage occurred since boot{volt_txt}; check battery output and cable."
        else:
            power_message = f"Voltage OK{volt_txt}; battery percentage requires telemetry hardware."
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        pass

    return {
        "throttled_raw": throttled_raw,
        "undervoltage_now": undervoltage_now,
        "undervoltage_occurred": undervoltage_occurred,
        "supply_voltage_v": voltage,
        "power_message": power_message,
    }
