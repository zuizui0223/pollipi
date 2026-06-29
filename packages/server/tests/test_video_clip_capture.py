"""HIGH=video: a strong-activity trigger records one clip and logs a video row.

Uses the fake camera and a stub controller so no hardware (and no real encoder) is
needed. A clip is a confirmation aid for strong local activity, never a confirmed visit.
"""
from __future__ import annotations

import csv
import importlib
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


def _clear() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def test_fake_camera_records_clip_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    _clear()
    from visit_monitor_server.adapters.fake_camera import FakeCamera

    cam = FakeCamera()
    cam.configure(cam.create_video_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 360)}))
    cam.start()
    clip = tmp_path / "clip_test.mp4"
    cam.start_video_clip(str(clip), fps=30)
    assert not clip.exists()  # file is finalized on stop, not start
    cam.stop_video_clip()
    assert clip.exists() and clip.stat().st_size > 0


def _video_log(images_dir: Path):
    files = sorted(images_dir.glob("adaptive_probe_shadow_v2_*.csv"))
    return files[0] if files else None


def test_high_trigger_records_clip_and_logs_video_row(monkeypatch, tmp_path) -> None:
    images = tmp_path / "images"
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_LIVE_ADAPTIVE_ENABLED", "1")
    monkeypatch.setenv("POLLIPI_PROBE_INTERVAL_SEC", "0.05")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(images))
    _clear()

    capture_loop = importlib.import_module("visit_monitor_server.services.capture_loop")
    from pollipi_analysis.policy.three_stage import ThreeStageConfig, ThreeStageOutput

    # Stub controller: probe 1 = MID still, probe 2 = HIGH video trigger, then MID.
    class StubController:
        def __init__(self) -> None:
            self.config = ThreeStageConfig(
                low_interval_sec=30.0, mid_interval_sec=10.0,
                high_mode="video", video_duration_sec=0.5, video_fps=30, video_cooldown_sec=45.0,
            )
            self._n = 0

        def step(self, decision_state, now_sec):
            self._n += 1
            if self._n == 2:
                return ThreeStageOutput(
                    mode="HIGH", interval_sec=10.0, reason="video_trigger_two_local_with_strong",
                    local_candidate_streak=0, quiet_streak=0, high_elapsed_sec=0.0, high_remaining_sec=0.0,
                    entered_high=True, exited_high=False, trigger_video=True,
                    cooldown_active=True, cooldown_remaining_sec=75.0,
                )
            return ThreeStageOutput(
                mode="MID", interval_sec=10.0, reason="mid_hold", local_candidate_streak=1,
                quiet_streak=0, high_elapsed_sec=0.0, high_remaining_sec=0.0,
                entered_high=False, exited_high=False, trigger_video=False,
                cooldown_active=False, cooldown_remaining_sec=0.0,
            )

    monkeypatch.setattr(capture_loop, "create_policy_controller", lambda profile: StubController())

    stop = threading.Event()
    request = SimpleNamespace(
        interval_sec=30,
        policy_profile_id="three_stage_video_canary_v1",  # real profile: live_allowed=true
        live_adaptive_requested=True,
    )
    thread = threading.Thread(
        target=capture_loop.run_capture_loop,
        args=(stop, request, images, threading.Lock(), lambda c: None, lambda d: None, lambda m: None),
        daemon=True,
    )
    thread.start()
    try:
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if list(images.glob("clip_*.mp4")):
                break
            time.sleep(0.1)
    finally:
        stop.set()
        thread.join(timeout=5.0)

    clips = list(images.glob("clip_*.mp4"))
    assert len(clips) == 1 and clips[0].stat().st_size > 0

    rows = list(csv.DictReader(_video_log(images).open(encoding="utf-8")))
    video_rows = [r for r in rows if r["record_kind"] == "video"]
    assert len(video_rows) == 1
    vr = video_rows[0]
    assert vr["video_filename"] == clips[0].name
    assert vr["trigger_reason"] == "video_trigger_two_local_with_strong"
    assert float(vr["video_duration_sec"]) > 0.0
    assert vr["video_fps"] == "30"
    assert vr["actual_highres_saved"] == "False"  # no still on the clip probe
    assert vr["live_adaptive_active"] == "True"
    assert vr["cooldown_active"] == "True"
