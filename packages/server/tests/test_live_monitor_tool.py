"""Unit coverage for the live-monitor smoke tool + the zuizui fleet config."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load(module_name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / rel_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_contains_jpeg_frame_detects_a_multipart_jpeg() -> None:
    tool = _load("check_live_monitor", "tools/check_live_monitor.py")
    # A multipart boundary plus a JPEG SOI marker counts as a real frame.
    assert tool.contains_jpeg_frame(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n\xff\xd8\xff\xe0rest")
    # Boundary without image data, or image data without boundary, do not.
    assert not tool.contains_jpeg_frame(b"--frame\r\n\r\nnot-an-image")
    assert not tool.contains_jpeg_frame(b"\xff\xd8\xff no boundary")
    assert not tool.contains_jpeg_frame(b"")


def test_zuizui_fleet_config_lists_five_units() -> None:
    fleet = _load("pollipi_fleet_deploy", "tools/pollipi_fleet_deploy.py")
    devices = fleet.load_devices(REPO_ROOT / "tools" / "fleet.zuizui.json")
    assert len(devices) == 5
    targets = {device.target for device in devices}
    assert targets == {
        "zuizui0223@zuizui.local",
        "zuizui0223@zuizui2.local",
        "zuizui0223@zuizui3.local",
        "zuizui0223@zuizui4.local",
        "zuizui0223@zuizui5.local",
    }
    for device in devices:
        assert device.base_url == f"http://{device.host}:8000"
