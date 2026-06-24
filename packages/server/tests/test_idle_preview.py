"""The monitor produces a true live preview when the timelapse is idle.

Before this, the monitor only served the latest scheduled image from disk, so an
idle device (nothing captured yet) showed no live view. The producer now opens a
dedicated preview camera while capture is not running. Verified here with the
fake camera and an empty image dir.
"""
from __future__ import annotations

import importlib
import sys
import time

import pytest


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _fresh_controller(monkeypatch, tmp_path):
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    _clear_server_modules()
    controller_mod = importlib.import_module("visit_monitor_server.services.controller")
    return controller_mod.TimelapseController(tmp_path / "images")


def test_idle_monitor_serves_live_preview_without_scheduled_image(monkeypatch, tmp_path) -> None:
    ctrl = _fresh_controller(monkeypatch, tmp_path)
    assert ctrl.latest_image() is None  # nothing captured yet

    # Keep a subscriber so the producer does not idle-timeout, then start it.
    ctrl._preview_subscriber_count = 1
    ctrl._start_monitor_producer()
    try:
        deadline = time.monotonic() + 5.0
        frame = None
        while time.monotonic() < deadline:
            frame = ctrl._latest_frame_bytes
            if frame is not None:
                break
            time.sleep(0.05)
    finally:
        captured = ctrl._latest_frame_bytes
        ctrl._preview_subscriber_count = 0
        ctrl._stop_monitor_producer()

    assert captured is not None, "idle producer did not yield a live preview frame"
    assert captured[:2] == b"\xff\xd8", "preview frame is not a JPEG"


def test_preview_camera_helpers_roundtrip(monkeypatch, tmp_path) -> None:
    ctrl = _fresh_controller(monkeypatch, tmp_path)
    cam = ctrl._open_preview_camera()
    try:
        frame = ctrl._grab_preview_jpeg(cam)
        assert frame is not None and frame[:2] == b"\xff\xd8"
    finally:
        ctrl._close_preview_camera(cam)
