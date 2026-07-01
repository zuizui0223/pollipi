"""The capture supervisor must survive a transient loop crash.

The loop runs in a daemon thread; when it raises, only that thread dies while
uvicorn stays up, so systemd never restarts and autonomous resume never re-arms.
The supervisor (`_run_loop`) therefore auto-restarts the loop after a backoff so
an unattended field Pi keeps capturing, and only gives up after repeated fast
crashes.
"""
from __future__ import annotations

import threading

import pytest

from visit_monitor_server.services import controller as ctrl_mod
from visit_monitor_server.services.controller import TimelapseController


def _controller(tmp_path) -> TimelapseController:
    c = TimelapseController(tmp_path)
    c._thread = threading.current_thread()  # so the finally's ownership check passes
    return c


def test_supervisor_auto_restarts_after_a_transient_crash(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ctrl_mod, "CAPTURE_LOOP_RESTART_DELAY_SEC", 0.0)
    calls = {"n": 0}

    def fake_loop(*, stop_event, **_kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient camera glitch")
        stop_event.set()  # second run behaves like a clean stop

    import visit_monitor_server.services.capture_loop as loop_mod
    monkeypatch.setattr(loop_mod, "run_capture_loop", fake_loop)

    c = _controller(tmp_path)
    c._run_loop(threading.Event(), request=object())

    assert calls["n"] == 2                     # crashed once, restarted, then stopped
    assert c.lifecycle_state == "stopped"      # recovered cleanly, not "error"


def test_supervisor_gives_up_after_max_fast_restarts(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ctrl_mod, "CAPTURE_LOOP_RESTART_DELAY_SEC", 0.0)
    monkeypatch.setattr(ctrl_mod, "CAPTURE_LOOP_MAX_RESTARTS", 3)
    import visit_monitor_server.services.capture_loop as loop_mod
    calls = {"n": 0}

    def always_crash(*, stop_event, **_kw):
        calls["n"] += 1
        raise RuntimeError("dead camera")

    monkeypatch.setattr(loop_mod, "run_capture_loop", always_crash)

    c = _controller(tmp_path)
    with pytest.raises(RuntimeError):
        c._run_loop(threading.Event(), request=object())

    assert calls["n"] == 3                      # tried up to the cap
    assert c.lifecycle_state == "error"         # then surfaced the failure


def test_supervisor_stop_during_backoff_is_clean(monkeypatch, tmp_path) -> None:
    stop = threading.Event()

    def crash_then_stop_is_requested(*, stop_event, **_kw):
        stop.set()  # a stop arrives right as the loop crashes
        raise RuntimeError("glitch at shutdown")

    import visit_monitor_server.services.capture_loop as loop_mod
    monkeypatch.setattr(loop_mod, "run_capture_loop", crash_then_stop_is_requested)

    c = _controller(tmp_path)
    c._run_loop(stop, request=object())

    assert c.lifecycle_state == "stopped"       # a stop during backoff is not an error
