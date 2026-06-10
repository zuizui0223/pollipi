"""Abstract camera interface (Protocol-based) for PolliPi.

All concrete camera implementations must expose this surface so that
the capture loop can work with both the real Picamera2 driver and the
synthetic FakeCamera used during CI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Camera(Protocol):
    """Minimal interface that every camera adapter must satisfy."""

    def configure(self, config) -> None:  # noqa: ANN001
        """Apply a camera configuration object."""
        ...

    def start(self) -> None:
        """Power up / open the camera sensor."""
        ...

    def stop(self) -> None:
        """Suspend capture."""
        ...

    def close(self) -> None:
        """Release all camera resources."""
        ...

    def capture_file(self, path: str, *, name: str = "main") -> None:
        """Write a JPEG frame to *path*."""
        ...

    def capture_array(self, name: str = "main"):  # noqa: ANN201
        """Return a raw numpy array (YUV420 lores or RGB main)."""
        ...

    def create_still_configuration(self, **kwargs):  # noqa: ANN201
        """Return an opaque config object for still capture."""
        ...

    def create_preview_configuration(self, **kwargs):  # noqa: ANN201
        """Return an opaque config object for preview / monitor."""
        ...
