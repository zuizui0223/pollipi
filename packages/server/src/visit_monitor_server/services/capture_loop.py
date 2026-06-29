"""Scheduled timelapse runtime with mesh shadow-mode metadata logging.

The active runtime saves scheduled timelapse images.  It uses the shared pure
``pollipi_analysis`` package to calculate an explainable three-state mesh decision
from low-resolution frames, but never claims a confirmed visit and never writes an
image-per-motion-event stream.
"""
from __future__ import annotations

import csv
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.policy import create_policy_controller, get_policy_profile
from visit_monitor_server.config import (
    ADAPTIVE_DECISION_LOG_PATH,
    CAMERA_LABEL,
    CAMERA_MODEL,
    CAMERA_PROFILE,
    DEVICE_ID,
    DEVICE_NAME,
    IS_AI_CAMERA,
    IS_NOIR,
    IS_WIDE,
    LIVE_ADAPTIVE_ENABLED,
    METRICS_PATH,
    MONITOR_SIZE,
    PROBE_INTERVAL_SEC,
    USE_FAKE_CAMERA,
    VIDEO_SIZE,
)

if TYPE_CHECKING:
    from visit_monitor_server.api.schemas.capture import StartRequest


SHADOW_COLUMNS = [
    "timestamp",
    "image_filename",
    "current_interval_sec",
    "would_be_next_interval_sec",
    "applied",
    "mesh_decision",
    "mesh_reason",
    "active_cell_proportion",
    "largest_component_cells",
    "concentration",
    "spatial_concentration",
    "offset_agreement",
    "persistence",
    "centroid_x",
    "centroid_y",
    "centroid_displacement",
    "path_efficiency",
    "direction_reversal",
    "global_synchrony",
    "estimated_global_shift",
    "device_id",
    "device_name",
    "site_id",
    "flower_id",
    "plant_species",
    "observer",
    "notes",
    "comparison_session_id",
    "camera_role",
    "method_mode",
    "policy_name",
    "policy_version",
    "validation_status",
    "policy_profile_id",
    "simulation_run_id",
    "kind",
    "live_allowed",
]


class _Picamera2Recorder:
    """Wrap a real Picamera2 so it satisfies the Camera Protocol's video clip API.

    Picamera2 records via ``start_recording(encoder, output)`` / ``stop_recording``;
    this adapter adds ``start_video_clip`` / ``stop_video_clip`` and delegates
    everything else (configure, capture_file, capture_array, create_*) unchanged.
    On a Pi 5 there is no hardware H.264 encoder, so H264Encoder runs in software.
    """

    def __init__(self, picam2) -> None:  # noqa: ANN001
        self._cam = picam2
        self._recording = False

    def __getattr__(self, name):  # delegate all non-video methods to Picamera2
        return getattr(self._cam, name)

    def start_video_clip(self, path: str, *, fps: int = 30, bitrate: int = 6_000_000) -> None:
        from picamera2.encoders import H264Encoder  # type: ignore
        from picamera2.outputs import FfmpegOutput  # type: ignore

        encoder = H264Encoder(bitrate=bitrate)
        self._cam.start_recording(encoder, FfmpegOutput(path))
        self._recording = True

    def stop_video_clip(self) -> None:
        if self._recording:
            self._cam.stop_recording()
            self._recording = False


def _open_camera():
    if USE_FAKE_CAMERA:
        from visit_monitor_server.adapters.fake_camera import FakeCamera
        return FakeCamera()
    from picamera2 import Picamera2  # type: ignore
    return _Picamera2Recorder(Picamera2())


def _write_shadow_record(
    captured_at: datetime,
    image_path: Path,
    current_interval_sec: float,
    would_be_next_interval_sec: float,
    decision,
    request,
    policy_meta=None,
    policy_profile=None,
) -> None:
    """Append compact scheduled-image metadata.  No candidate-event image exists."""
    write_header = not METRICS_PATH.exists()
    features = decision.features
    with METRICS_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(SHADOW_COLUMNS)
        writer.writerow([
            captured_at.isoformat(timespec="seconds"),
            image_path.name,
            f"{current_interval_sec:.3f}",
            f"{would_be_next_interval_sec:.3f}",
            False,
            decision.state,
            decision.reason,
            features.active_cell_proportion,
            features.largest_component_cells,
            features.concentration,
            features.spatial_concentration,
            features.offset_agreement,
            features.persistence,
            features.centroid_x,
            features.centroid_y,
            features.centroid_displacement,
            features.path_efficiency,
            features.direction_reversal,
            features.global_synchrony,
            features.estimated_global_shift,
            DEVICE_ID,
            DEVICE_NAME,
            request.site_id or "",
            request.flower_id or "",
            request.plant_species or "",
            request.observer or "",
            request.notes or "",
            request.comparison_session_id or "",
            request.camera_role or "",
            request.method_mode or "",
            getattr(policy_meta, "policy_name", "baseline_rule"),
            getattr(policy_meta, "policy_version", "0"),
            getattr(policy_meta, "validation_status", "synthetic_only"),
            getattr(policy_profile, "profile_id", getattr(request, "policy_profile_id", "") or ""),
            getattr(policy_profile, "simulation_run_id", ""),
            getattr(policy_profile, "kind", ""),
            getattr(policy_profile, "live_allowed", False),
        ])

    decision_header = not ADAPTIVE_DECISION_LOG_PATH.exists()
    with ADAPTIVE_DECISION_LOG_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if decision_header:
            writer.writerow([
                "timestamp",
                "current_interval_sec",
                "would_be_next_interval_sec",
                "mesh_decision",
                "mesh_reason",
                "applied",
            ])
        writer.writerow([
            captured_at.isoformat(timespec="seconds"),
            f"{current_interval_sec:.3f}",
            f"{would_be_next_interval_sec:.3f}",
            decision.state,
            decision.reason,
            False,
        ])


# Per-run probe shadow log (data contract v2). A new file is created for each run
# (adaptive_probe_shadow_v2_<run_id>.csv); the legacy mixed-schema v1 file is no
# longer appended to. saved_image_filename / scheduled_highres_timestamp / run_id
# give a robust join key, and applied_interval_sec / live_adaptive_active record
# the interval actually used so "why 5 s" is traceable after the fact.
PROBE_SHADOW_V2_SCHEMA = "probe-shadow-2"
PROBE_SHADOW_V2_COLUMNS = [
    "schema_version",
    "run_id",
    "probe_timestamp",
    "probe_interval_sec",
    "would_be_mode",
    "would_be_interval_sec",
    "applied_interval_sec",
    "live_adaptive_active",
    "decision_state",
    "decision_reason",
    "local_candidate_streak",
    "quiet_streak",
    "high_elapsed_sec",
    "high_remaining_sec",
    "actual_highres_saved",
    "saved_image_filename",
    "scheduled_highres_timestamp",
    "next_highres_due_at",
    "record_kind",
    "video_filename",
    "video_started_at",
    "video_duration_sec",
    "video_fps",
    "trigger_reason",
    "cooldown_active",
    "cooldown_remaining_sec",
    "device_id",
    "policy_profile_id",
    "simulation_run_id",
    "kind",
    "live_allowed",
    "policy_name",
    "policy_version",
    "validation_status",
]


def probe_log_path(image_dir: Path, run_id: str) -> Path:
    return image_dir / f"adaptive_probe_shadow_v2_{run_id}.csv"


def live_adaptive_active(request, policy_profile) -> bool:
    """Live adaptive timing applies only when ALL three gates are true:

    POLLIPI_LIVE_ADAPTIVE_ENABLED=1 AND profile.live_allowed=true AND the
    /start request set live_adaptive_requested=true. Otherwise capture timing is
    the fixed scheduled interval (shadow-only) and this returns False.
    """
    return bool(
        LIVE_ADAPTIVE_ENABLED
        and getattr(policy_profile, "live_allowed", False)
        and getattr(request, "live_adaptive_requested", False)
    )


def compute_next_due(last_highres_mono: Optional[float], desired_interval_sec: float, now_mono: float) -> float:
    """Next high-res due time = last save + the *current* desired interval.

    Recomputed every probe so a mode change (e.g. -> HIGH/5 s) takes effect on the
    next probe instead of waiting out a previously scheduled longer interval.
    The first frame (no prior save) is due immediately.
    """
    if last_highres_mono is None:
        return now_mono
    return last_highres_mono + desired_interval_sec


def _write_probe_record_v2(
    path: Path,
    run_id: str,
    probe_at: datetime,
    probe_interval_sec: float,
    out,
    applied_interval_sec: float,
    live_active: bool,
    decision_state: str,
    decision_reason: str,
    actual_highres_saved: bool,
    saved_image_filename: str,
    scheduled_highres_timestamp: str,
    next_highres_due_at: str,
    policy_meta,
    policy_profile,
    record_kind: str = "image",
    video_filename: str = "",
    video_started_at: str = "",
    video_duration_sec: str = "",
    video_fps: str = "",
    trigger_reason: str = "",
    cooldown_active: bool = False,
    cooldown_remaining_sec: float = 0.0,
) -> None:
    """Append one row per low-resolution probe to the per-run v2 log."""
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(PROBE_SHADOW_V2_COLUMNS)
        writer.writerow([
            PROBE_SHADOW_V2_SCHEMA,
            run_id,
            probe_at.isoformat(timespec="seconds"),
            f"{probe_interval_sec:.3f}",
            out.mode,
            f"{out.interval_sec:.3f}",
            f"{applied_interval_sec:.3f}",
            live_active,
            decision_state,
            decision_reason,
            out.local_candidate_streak,
            out.quiet_streak,
            f"{out.high_elapsed_sec:.3f}",
            f"{out.high_remaining_sec:.3f}",
            actual_highres_saved,
            saved_image_filename,
            scheduled_highres_timestamp,
            next_highres_due_at,
            record_kind,
            video_filename,
            video_started_at,
            video_duration_sec,
            video_fps,
            trigger_reason,
            cooldown_active,
            f"{cooldown_remaining_sec:.3f}",
            DEVICE_ID,
            policy_profile.profile_id,
            policy_profile.simulation_run_id,
            policy_profile.kind,
            policy_profile.live_allowed,
            getattr(policy_meta, "policy_name", "baseline_rule"),
            getattr(policy_meta, "policy_version", "0"),
            getattr(policy_meta, "validation_status", "synthetic_only"),
        ])


def _record_clip(camera, camera_lock, clip_path, duration_sec, fps, stop_event) -> float:
    """Record one video clip, polling stop_event; always finalize the file.

    Returns the actual recorded duration. stop_video_clip runs in a finally so a
    stop request or error mid-clip never leaves the encoder running or the file
    unflushed. The camera_lock is held only to start/stop, not for the whole clip.
    """
    start = time.monotonic()
    with camera_lock:
        camera.start_video_clip(str(clip_path), fps=fps)
    try:
        deadline = start + duration_sec
        while not stop_event.is_set() and time.monotonic() < deadline:
            stop_event.wait(0.5)
    finally:
        with camera_lock:
            camera.stop_video_clip()
    return time.monotonic() - start


def run_capture_loop(
    stop_event: threading.Event,
    request,
    image_dir: Path,
    camera_lock: threading.Lock,
    set_camera,
    update_state,
    set_message,
    trainer=None,
) -> None:
    """Run scheduled capture and shadow-mode mesh analysis.

    ``trainer`` remains a no-op compatibility argument while older controller
    construction code is being removed.  The active runtime does not use ML.
    """
    del trainer
    camera = None
    previous_frame = None
    previous_active_cells = None
    previous_centroid = None

    try:
        image_dir.mkdir(parents=True, exist_ok=True)

        # Issue #21: load the (simulation-informed) policy artifact + selected profile
        # BEFORE configuring the camera, so a live video-HIGH run can pick the video
        # configuration up front (no mid-run reconfiguration). The Pi only consumes
        # numeric thresholds here — no simulation/search runs.
        from visit_monitor_server.services.policy_runtime import get_active_policy

        policy_config, policy_meta = get_active_policy()
        policy_profile = get_policy_profile(request.policy_profile_id)

        # Issue #27 probe-only three-stage shadow. Two clocks:
        #  - low-resolution probe every PROBE_INTERVAL_SEC (no JPEG saved),
        #  - high-resolution JPEG on the fixed scheduled interval.
        hires_interval = float(request.interval_sec)
        probe_interval = min(PROBE_INTERVAL_SEC, hires_interval)
        three = create_policy_controller(policy_profile)

        # Live adaptive timing applies only behind the three-gate guard. When it is
        # off (the default) the high-res interval stays fixed (shadow-only).
        live_active = live_adaptive_active(request, policy_profile)
        # In live modes both intervals are user-set: the normal interval (interval_sec)
        # is LOW, and the high-frequency interval (fast_interval_sec, validated < normal)
        # is MID. When fast is omitted the profile's mid_interval_sec stays the default.
        if live_active:
            fast = (
                float(request.fast_interval_sec)
                if getattr(request, "fast_interval_sec", None)
                else three.config.mid_interval_sec
            )
            three.config = replace(
                three.config, low_interval_sec=hires_interval, mid_interval_sec=fast
            )
        # Video clips need the video configuration (1080p main + lores probe). Only a
        # live video-mode run switches to it; every other run keeps the original
        # still configuration (full-resolution stills) unchanged.
        use_video_config = live_active and three.config.high_mode == "video"

        run_started = datetime.now().astimezone()
        run_id = f"{DEVICE_ID}_{run_started.strftime('%Y%m%dT%H%M%S')}"
        probe_log = probe_log_path(image_dir, run_id)

        with camera_lock:
            camera = _open_camera()
            if use_video_config:
                camera.configure(
                    camera.create_video_configuration(
                        main={"size": VIDEO_SIZE},
                        lores={"size": MONITOR_SIZE, "format": "YUV420"},
                    )
                )
            else:
                camera.configure(
                    camera.create_still_configuration(
                        lores={"size": MONITOR_SIZE, "format": "YUV420"}
                    )
                )
            camera.start()
        set_camera(camera)

        if stop_event.wait(2):
            return
        set_message("Scheduled timelapse running; mesh decisions are logged in shadow mode.")

        update_state({
            "probe_interval_sec": probe_interval,
            "would_be_mode": "LOW",
            "would_be_interval_sec": three.config.low_interval_sec,
            "policy_profile_id": policy_profile.profile_id,
            "simulation_run_id": policy_profile.simulation_run_id,
            "kind": policy_profile.kind,
            "live_allowed": policy_profile.live_allowed,
            "live_adaptive_active": live_active,
            "interval_sec": three.config.low_interval_sec if live_active else hires_interval,
            "message": (
                "Probe-only three-stage; LIVE adaptive interval active."
                if live_active
                else "Probe-only three-stage shadow; high-res capture fixed."
            ),
        })

        last_highres_mono = None  # monotonic time of the last saved high-res frame

        while not stop_event.is_set():
            now_mono = time.monotonic()
            captured_at = datetime.now().astimezone()

            with camera_lock:
                frame = camera.capture_array("lores")

            if previous_frame is None:
                decision = None
                decision_state = "no_activity"
                decision_reason = "waiting_for_reference_frame"
            else:
                decision = analyze(
                    frame,
                    previous_frame,
                    config=policy_config,
                    previous_active_cells=previous_active_cells,
                    previous_centroid=previous_centroid,
                )
                decision_state = decision.state
                decision_reason = decision.reason
                previous_active_cells = set(decision.active_cells)
                if decision.features.centroid_x is not None and decision.features.centroid_y is not None:
                    previous_centroid = (decision.features.centroid_x, decision.features.centroid_y)
            previous_frame = frame

            out = three.step(decision_state, now_mono)

            # Desired high-res interval: the three-stage interval when live adaptive
            # is active, otherwise the fixed scheduled interval.
            desired_interval = out.interval_sec if live_active else hires_interval

            record_kind = "image"
            video_filename = ""
            video_started_at = ""
            video_duration_str = ""
            video_fps_str = ""
            trigger_reason = ""
            actual_highres_saved = False
            saved_image_filename = ""
            scheduled_highres_timestamp = ""

            if use_video_config and out.trigger_video:
                # HIGH = one video clip; no still this probe ("動画中は静止画不要").
                clip_name = captured_at.strftime("clip_%Y%m%d_%H%M%S_") + run_id + ".mp4"
                clip_path = image_dir / clip_name
                video_started_at = captured_at.isoformat(timespec="seconds")
                actual_duration = _record_clip(
                    camera, camera_lock, clip_path,
                    three.config.video_duration_sec, three.config.video_fps, stop_event,
                )
                # The clip is the HIGH record; reset the still schedule so MID stills
                # resume relative to the clip's end, not the moment it started.
                last_highres_mono = time.monotonic()
                record_kind = "video"
                video_filename = clip_name
                video_duration_str = f"{actual_duration:.3f}"
                video_fps_str = str(three.config.video_fps)
                trigger_reason = out.reason
                update_state({
                    "capture_count_delta": 1,
                    "last_capture_time": captured_at.isoformat(timespec="seconds"),
                    "last_image": str(clip_path),
                })
            else:
                # Re-derive the next high-res due time every probe from the last save
                # plus the current desired interval, so a mode change shortens the very
                # next capture instead of waiting out the old interval.
                due_mono = compute_next_due(last_highres_mono, desired_interval, now_mono)
                if now_mono >= due_mono:
                    filename = captured_at.strftime("image_%Y%m%d_%H%M%S_%f.jpg")
                    image_path = image_dir / filename
                    with camera_lock:
                        camera.capture_file(str(image_path))
                    actual_highres_saved = True
                    saved_image_filename = filename
                    scheduled_highres_timestamp = captured_at.isoformat(timespec="seconds")
                    last_highres_mono = now_mono
                    if decision is not None:
                        _write_shadow_record(
                            captured_at,
                            image_path,
                            desired_interval,
                            out.interval_sec,
                            decision,
                            request,
                            policy_meta,
                            policy_profile,
                        )
                    update_state({
                        "capture_count_delta": 1,
                        "last_capture_time": captured_at.isoformat(timespec="seconds"),
                        "last_image": str(image_path),
                    })

            next_due_mono = compute_next_due(last_highres_mono, desired_interval, now_mono)
            next_due_at = (captured_at + timedelta(seconds=max(0.0, next_due_mono - now_mono))).isoformat(timespec="seconds")
            _write_probe_record_v2(
                probe_log, run_id, captured_at, probe_interval, out, desired_interval, live_active,
                decision_state, decision_reason, actual_highres_saved, saved_image_filename,
                scheduled_highres_timestamp, next_due_at, policy_meta, policy_profile,
                record_kind=record_kind, video_filename=video_filename,
                video_started_at=video_started_at, video_duration_sec=video_duration_str,
                video_fps=video_fps_str, trigger_reason=trigger_reason,
                cooldown_active=out.cooldown_active, cooldown_remaining_sec=out.cooldown_remaining_sec,
            )

            mesh_state = {
                "mesh_decision": decision_state,
                "mesh_reason": decision_reason,
                "mesh_active_cell_proportion": decision.features.active_cell_proportion if decision else 0.0,
                "mesh_offset_agreement": decision.features.offset_agreement if decision else 0.0,
                "mesh_global_synchrony": decision.features.global_synchrony if decision else 0.0,
            }
            update_state({
                "interval_sec": desired_interval,  # interval actually applied to the schedule
                "next_interval_sec": desired_interval,
                "would_be_mode": out.mode,
                "would_be_interval_sec": out.interval_sec,
                "live_adaptive_active": live_active,
                "policy_profile_id": policy_profile.profile_id,
                "simulation_run_id": policy_profile.simulation_run_id,
                "kind": policy_profile.kind,
                "live_allowed": policy_profile.live_allowed,
                "interval_reason": (
                    f"LIVE adaptive: mode {out.mode} -> {desired_interval:.0f}s; {decision_reason}."
                    if live_active
                    else (
                        f"Probe shadow: would-be {out.mode} ({out.interval_sec:.0f}s); "
                        f"{decision_reason}; high-res fixed at {hires_interval:.0f}s."
                    )
                ),
                **mesh_state,
            })

            # The probe cadence governs the loop; high-res timing follows
            # desired_interval (fixed unless the live-adaptive guard is satisfied).
            if stop_event.wait(probe_interval):
                break

    except Exception as exc:
        set_message(f"Capture error: {exc}")
        raise
    finally:
        if camera is not None:
            with camera_lock:
                try:
                    camera.stop()
                finally:
                    camera.close()
        set_camera(None)
