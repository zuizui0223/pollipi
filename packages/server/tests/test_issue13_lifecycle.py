from __future__ import annotations

import threading
import time

from visit_monitor_server.services.controller import TimelapseController
from visit_monitor_server.services.ws_supervisor import ReconnectPolicy, WebSocketReconnectSupervisor


def test_stop_uses_bounded_join_and_keeps_stopping_state(tmp_path):
    controller = TimelapseController(tmp_path)
    controller.stop_timeout_sec = 0.02
    stop_event = threading.Event()
    thread = threading.Thread(target=lambda: time.sleep(0.2), daemon=True)
    thread.start()
    with controller._lock:
        controller.running = True
        controller.lifecycle_state = "running"
        controller._stop_event = stop_event
        controller._thread = thread

    status = controller.stop()

    assert stop_event.is_set()
    assert status.lifecycle_state == "stopping"
    assert status.running is False
    assert "did not exit" in status.message


def test_capture_exception_is_persisted_in_status(tmp_path, monkeypatch):
    controller = TimelapseController(tmp_path)

    def fail_loop(**_kwargs):
        raise RuntimeError("camera busy")

    monkeypatch.setattr("visit_monitor_server.services.capture_loop.run_capture_loop", fail_loop)
    stop_event = threading.Event()
    request = object()
    with controller._lock:
        controller._thread = threading.current_thread()

    try:
        controller._run_loop(stop_event, request)
    except RuntimeError:
        pass

    status = controller.status()
    assert status.lifecycle_state == "error"
    assert status.last_error == "RuntimeError: camera busy"


def test_future_websocket_reconnect_policy_is_bounded_and_resettable():
    supervisor = WebSocketReconnectSupervisor(
        ReconnectPolicy(initial_delay_sec=1, max_delay_sec=5, multiplier=2, jitter_fraction=0),
    )

    assert [supervisor.record_failure() for _ in range(4)] == [1, 2, 4, 5]
    supervisor.record_success()
    assert supervisor.record_failure() == 1
