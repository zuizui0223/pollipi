"""Monitor preview lifecycle must be capture-safe (R1).

The preview producer must never run during scheduled capture, stale subscribers
must be reaped (no permanently-stuck producer), and capture must not depend on
the preview subscriber state.
"""
from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

import pytest


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _fresh(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    _clear_server_modules()
    controller_mod = importlib.import_module("visit_monitor_server.services.controller")
    capture_schemas = importlib.import_module("visit_monitor_server.api.schemas.capture")
    ctrl = controller_mod.TimelapseController(tmp_path / "images")
    return ctrl, capture_schemas.StartRequest


def _wait_until(predicate, timeout=4.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def test_normal_stream_end_decrements_subscribers(monkeypatch, tmp_path) -> None:
    ctrl, _ = _fresh(monkeypatch, tmp_path)
    gen = ctrl.monitor_frames()
    ctrl._latest_frame_bytes = b"\xff\xd8frame"  # inject so the first next() yields
    try:
        chunk = next(gen)
        assert b"\xff\xd8" in chunk
        assert ctrl._active_subscriber_count() == 1
        gen.close()  # normal stream end runs the finally
        assert ctrl._active_subscriber_count() == 0
        assert _wait_until(lambda: ctrl._preview_producer_state == "idle")
    finally:
        gen.close()
        ctrl._stop_monitor_producer()


def test_stale_subscriber_is_reaped_after_timeout(monkeypatch, tmp_path) -> None:
    ctrl, _ = _fresh(monkeypatch, tmp_path)
    sid = ctrl._register_subscriber()
    assert ctrl._active_subscriber_count() == 1
    # Simulate a subscriber that stopped refreshing (unclean disconnect) by aging it.
    ctrl._subscribers[sid] = time.monotonic() - (ctrl._subscriber_stale_after + 1.0)
    assert ctrl._active_subscriber_count() == 0  # reaped, not trusted as live


def test_capture_start_stops_monitor_producer(monkeypatch, tmp_path) -> None:
    ctrl, StartRequest = _fresh(monkeypatch, tmp_path)
    ctrl._register_subscriber()
    ctrl._start_monitor_producer()
    assert _wait_until(lambda: ctrl._monitor_thread is not None and ctrl._monitor_thread.is_alive())
    try:
        ctrl.start(StartRequest(interval_sec=2))
        # Producer must be stopped by capture start (server-side, not PWA-driven).
        assert _wait_until(lambda: ctrl._preview_producer_state == "idle")
        assert ctrl._monitor_thread is None
    finally:
        ctrl.stop()


def test_producer_does_not_start_during_capture(monkeypatch, tmp_path) -> None:
    ctrl, _ = _fresh(monkeypatch, tmp_path)
    with ctrl._lock:
        ctrl.running = True  # simulate capture active
    # Guard: producer must not start while capture runs.
    ctrl._start_monitor_producer()
    assert ctrl._monitor_thread is None
    assert ctrl._preview_producer_state == "idle"
    # And a new /mjpeg stream is refused (empty generator) without registering.
    gen = ctrl.monitor_frames()
    with pytest.raises(StopIteration):
        next(gen)
    assert ctrl._active_subscriber_count() == 0


def test_leftover_subscribers_do_not_block_capture(monkeypatch, tmp_path) -> None:
    ctrl, StartRequest = _fresh(monkeypatch, tmp_path)
    # Leftover/stuck subscriber entries from previous streams.
    for _ in range(13):
        ctrl._register_subscriber()
    try:
        status = ctrl.start(StartRequest(interval_sec=2))
        assert status.running is True  # capture proceeds regardless of subscribers
    finally:
        ctrl.stop()


def test_active_count_reflects_live_streams_not_a_raw_counter(monkeypatch, tmp_path) -> None:
    ctrl, _ = _fresh(monkeypatch, tmp_path)
    a = ctrl._register_subscriber()
    b = ctrl._register_subscriber()
    assert ctrl._active_subscriber_count() == 2
    ctrl._remove_subscriber(a)
    assert ctrl._active_subscriber_count() == 1
    ctrl._remove_subscriber(b)
    assert ctrl._active_subscriber_count() == 0
