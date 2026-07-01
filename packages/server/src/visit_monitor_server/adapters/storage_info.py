"""Discover external-storage candidates (USB drives, mounts) for the /storage API.

The Raspberry Pi OS desktop automounts removable drives under
``/media/<user>/<LABEL>``; headless / manual mounts usually live under
``/mnt/<name>``. This module scans both, plus the SD-card default and the
currently-active directory, and reports free space and writability for each so
the web app can present a pick-list. Nothing here creates the image directory —
inspection is side-effect free; the actual mkdir happens only when a target is
selected via ``POST /storage``.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

_MEDIA_ROOT = Path("/media")
_MNT_ROOT = Path("/mnt")
# Convention: an external drive mounted at <mount> stores photos under
# <mount>/images (matches the documented /media/<user>/<LABEL>/images layout).
_IMAGES_SUBDIR = "images"


def _existing_ancestor(path: Path) -> Path:
    """Return *path* or its nearest existing ancestor (for stat-ing free space)."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def _is_writable(path: Path) -> bool:
    return os.access(str(_existing_ancestor(path)), os.W_OK)


def _describe(image_dir: Path, mount: Optional[Path]) -> dict:
    probe = _existing_ancestor(image_dir)
    try:
        usage = shutil.disk_usage(str(probe))
        total, used, free = usage.total, usage.used, usage.free
        percent = round(used / total * 100, 1) if total else 0.0
    except OSError:
        total = used = free = 0
        percent = 0.0
    return {
        "path": str(image_dir),
        "mount": str(mount) if mount is not None else None,
        "exists": image_dir.exists(),
        "writable": _is_writable(image_dir),
        "is_mount": mount is not None and os.path.ismount(str(mount)),
        "storage_total_bytes": total,
        "storage_used_bytes": used,
        "storage_free_bytes": free,
        "storage_percent_used": percent,
    }


def _safe_iterdir(path: Path) -> list[Path]:
    try:
        return sorted(p for p in path.iterdir() if p.is_dir())
    except OSError:
        return []


def _iter_mounts() -> list[Path]:
    """Return candidate external mount points under /media and /mnt."""
    mounts: list[Path] = []
    if _MEDIA_ROOT.is_dir():
        for user_dir in _safe_iterdir(_MEDIA_ROOT):
            # /media/<user>/<LABEL> automount layout: descend one level.
            grandchildren = _safe_iterdir(user_dir)
            if grandchildren:
                mounts.extend(grandchildren)
            elif os.path.ismount(str(user_dir)):
                mounts.append(user_dir)
    if _MNT_ROOT.is_dir():
        mounts.extend(_safe_iterdir(_MNT_ROOT))
    return mounts


def discover_targets(current: Path, default: Path) -> list[dict]:
    """List selectable storage targets: SD default, current, and detected mounts."""
    targets: dict[str, dict] = {}

    def add(image_dir: Path, mount: Optional[Path], label: str, kind: str) -> None:
        key = str(image_dir)
        if key in targets:
            return
        info = _describe(image_dir, mount)
        info.update(
            label=label,
            kind=kind,
            is_current=(image_dir == current),
            is_default=(image_dir == default),
        )
        targets[key] = info

    add(default, None, "SD card (default)", "internal")
    if current != default:
        add(current, current.parent, "Current selection", "external")
    for mount in _iter_mounts():
        add(mount / _IMAGES_SUBDIR, mount, mount.name, "external")

    return list(targets.values())
