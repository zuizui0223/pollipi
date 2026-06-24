#!/usr/bin/env python3
"""Build the deployable PolliPi server artifact on any supported OS.

The package-level npm script used to rely on POSIX-only ``PYTHONPATH=...``
syntax, which fails in Windows PowerShell. Keeping the import setup in Python
makes the documented build command work consistently on Windows, macOS,
Linux, and WSL.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SERVER_SOURCE = REPOSITORY_ROOT / "packages" / "server" / "src"
ARTIFACT_PATH = REPOSITORY_ROOT / "dist" / "pollipi_api_server.py"


def main() -> None:
    if str(SERVER_SOURCE) not in sys.path:
        sys.path.insert(0, str(SERVER_SOURCE))

    from visit_monitor_server.distribution.bundle_single_file import build

    artifact = build(ARTIFACT_PATH)
    try:
        display_path = artifact.relative_to(REPOSITORY_ROOT)
    except ValueError:
        display_path = artifact
    print(f"Wrote {display_path}")


if __name__ == "__main__":
    main()
