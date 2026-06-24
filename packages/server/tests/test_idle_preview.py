"""Idle MJPEG preview should produce frames before any scheduled image exists."""
from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _fresh_controller(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    _clear_server_modules()
    controller_mod = importlib.import_module("visit_monitor_server.services.controller")
    return controller_mod.TimelapseController(tmp_path / "images")


def test_idle_monitor_serves_live_preview_without_scheduled_image(monkeypatch, tmp_path) -> None:
    ctrl = _fresh_controller(monkeypatch, tmp_path)
    assert ctrl.latest_image() is None

    ctrl._preview_subscriber_count = 1
    ctrl._start_monitor_producer()
    try:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and ctrl._latest_frame_bytes is None:
            time.sleep(0.05)
        captured = ctrl._latest_frame_bytes
    finally:
        ctrl._preview_subscriber_count = 0
        ctrl._stop_monitor_producer()

    assert captured is not None
    assert captured[:2] == b"\xff\xd8"


def test_preview_camera_helpers_roundtrip(monkeypatch, tmp_path) -> None:
    ctrl = _fresh_controller(monkeypatch, tmp_path)
    cam = ctrl._open_preview_camera()
    try:
        frame = ctrl._grab_preview_jpeg(cam)
        assert frame is not None and frame[:2] == b"\xff\xd8"
    finally:
        ctrl._close_preview_camera(cam)
