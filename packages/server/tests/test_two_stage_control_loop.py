"""Phase 4: live two-stage control is off by default and applies timing when on.

Uses the fresh-import pattern so the loop's deferred imports and config resolve
to this test's environment regardless of other tests reloading the package.
"""
from __future__ import annotations

import csv
import importlib
import sys
import threading
import time

import pytest

pytest.importorskip("numpy")


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _run_loop_until(metrics_predicate_path, *, request_kwargs, monkeypatch, tmp_path):
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    monkeypatch.delenv("POLLIPI_ADAPTIVE_CONTROL", raising=False)

    _clear_server_modules()
    config = importlib.import_module("visit_monitor_server.config")
    cl = importlib.import_module("visit_monitor_server.services.capture_loop")
    capture_schema = importlib.import_module("visit_monitor_server.api.schemas.capture")

    metrics_path = config.METRICS_PATH
    request = capture_schema.StartRequest(**request_kwargs)
    stop_event = threading.Event()
    error: list[BaseException] = []

    def run() -> None:
        try:
            cl.run_capture_loop(
                stop_event,
                request,
                tmp_path / "images",
                threading.Lock(),
                set_camera=lambda *_: None,
                update_state=lambda *_: None,
                set_message=lambda *_: None,
            )
        except BaseException as exc:  # noqa: BLE001
            error.append(exc)

    worker = threading.Thread(target=run)
    worker.start()
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline and not metrics_path.exists() and not error:
        time.sleep(0.1)
    stop_event.set()
    worker.join(timeout=10.0)
    assert not error, f"capture loop raised: {error}"
    return metrics_path


def _read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_control_enabled_applies_timing(monkeypatch, tmp_path) -> None:
    metrics_path = _run_loop_until(
        None,
        request_kwargs=dict(
            interval_sec=1,
            two_stage_control=True,
            low_rate_sec=1,
            high_rate_sec=1,
            high_hold_sec=5,
        ),
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )
    assert metrics_path.exists()
    rows = _read_rows(metrics_path)
    assert rows
    # With live control on, the analysed capture's interval is applied.
    assert all(r["applied"] == "True" for r in rows)


def test_control_disabled_by_default_is_shadow_only(monkeypatch, tmp_path) -> None:
    metrics_path = _run_loop_until(
        None,
        request_kwargs=dict(interval_sec=1),
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )
    assert metrics_path.exists()
    rows = _read_rows(metrics_path)
    assert rows
    # Default: timing is never changed (shadow only).
    assert all(r["applied"] == "False" for r in rows)
