"""Explicit default-off instrumentation for probability-audit probe capture.

The active capture loop predates the generic V3/REC/TNOA audit contract.  To avoid
mixing benchmark storage logic into policy/timing code, this module installs a small
set of wrappers at application startup:

* the existing TNOA builder exposes the current low-resolution frame;
* the existing three-stage policy step exposes the would-be selection state;
* the existing TNOA log call supplies the stable run/device/probe identity;
* an outer run wrapper finalizes edge/incomplete audit centres.

When ``POLLIPI_AUDIT_ENABLED`` is false (the default), the wrappers preserve the
existing behavior and perform no audit storage.  When enabled, configuration is
validated at application startup and live adaptive capture is rejected.
"""
from __future__ import annotations

import threading
from functools import wraps
from pathlib import Path
from typing import Any

from visit_monitor_server.services.audit_capture import (
    AuditCaptureConfig,
    AuditCaptureManager,
)

_installed = False
_state = threading.local()
_config = AuditCaptureConfig(enabled=False)


class _PolicyControllerProxy:
    """Forward policy-controller attributes while observing ``step`` outputs."""

    def __init__(self, inner: Any) -> None:
        object.__setattr__(self, "_inner", inner)

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_inner"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_inner":
            object.__setattr__(self, name, value)
        else:
            setattr(object.__getattribute__(self, "_inner"), name, value)

    def step(self, *args: Any, **kwargs: Any) -> Any:
        out = object.__getattribute__(self, "_inner").step(*args, **kwargs)
        _state.latest_policy_output = out
        return out


def _clear_probe_state() -> None:
    _state.latest_frame = None
    _state.latest_policy_output = None


def _finalize_manager() -> None:
    manager = getattr(_state, "manager", None)
    try:
        if manager is not None:
            manager.finalize()
    finally:
        _state.manager = None
        _clear_probe_state()


def install_audit_capture_instrumentation() -> None:
    """Install idempotent wrappers around the existing capture-loop surfaces."""

    global _installed, _config
    if _installed:
        return

    # Validate all benchmark settings before the application begins capturing.
    _config = AuditCaptureConfig.from_environment()

    import visit_monitor_server.services.capture_loop as capture_loop

    original_build_tnoa = capture_loop.build_tnoa_shadow_record
    original_create_controller = capture_loop.create_policy_controller
    original_write_tnoa = capture_loop.write_tnoa_shadow_record
    original_live_active = capture_loop.live_adaptive_active
    original_run = capture_loop.run_capture_loop

    @wraps(original_build_tnoa)
    def build_tnoa_wrapper(*args: Any, **kwargs: Any) -> Any:
        frame = args[1] if len(args) >= 2 else kwargs.get("frame")
        if _config.enabled:
            if frame is None:
                raise RuntimeError("audit instrumentation could not observe probe frame")
            _state.latest_frame = frame
        return original_build_tnoa(*args, **kwargs)

    @wraps(original_create_controller)
    def create_controller_wrapper(*args: Any, **kwargs: Any) -> Any:
        return _PolicyControllerProxy(original_create_controller(*args, **kwargs))

    @wraps(original_write_tnoa)
    def write_tnoa_wrapper(path: Path, *args: Any, **kwargs: Any) -> Any:
        result = original_write_tnoa(path, *args, **kwargs)
        if not _config.enabled:
            return result

        frame = getattr(_state, "latest_frame", None)
        out = getattr(_state, "latest_policy_output", None)
        if frame is None or out is None:
            raise RuntimeError(
                "audit instrumentation lost frame/policy alignment for a probe"
            )

        run_id = str(kwargs.get("run_id", ""))
        device_id = str(kwargs.get("device_id", ""))
        probe_at = kwargs.get("probe_at")
        if not run_id or not device_id or probe_at is None:
            raise RuntimeError("audit instrumentation requires run_id/device_id/probe_at")

        manager = getattr(_state, "manager", None)
        if manager is None:
            manager = AuditCaptureManager(
                image_dir=Path(path).parent,
                run_id=run_id,
                device_id=device_id,
                config=_config,
            )
            _state.manager = manager

        probe_timestamp = probe_at.isoformat(timespec="seconds")
        manager.add_probe(
            frame=frame,
            probe_timestamp=probe_timestamp,
            selected=str(getattr(out, "mode", "")).upper() != "LOW",
        )
        _clear_probe_state()
        return result

    @wraps(original_live_active)
    def live_active_wrapper(*args: Any, **kwargs: Any) -> bool:
        active = bool(original_live_active(*args, **kwargs))
        if active and _config.enabled:
            raise RuntimeError(
                "POLLIPI_AUDIT_ENABLED requires shadow-only capture; live adaptive is forbidden"
            )
        return active

    @wraps(original_run)
    def run_wrapper(*args: Any, **kwargs: Any) -> Any:
        _state.manager = None
        _clear_probe_state()
        try:
            return original_run(*args, **kwargs)
        finally:
            _finalize_manager()

    capture_loop.build_tnoa_shadow_record = build_tnoa_wrapper
    capture_loop.create_policy_controller = create_controller_wrapper
    capture_loop.write_tnoa_shadow_record = write_tnoa_wrapper
    capture_loop.live_adaptive_active = live_active_wrapper
    capture_loop.run_capture_loop = run_wrapper
    _installed = True
