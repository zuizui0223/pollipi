#!/usr/bin/env python3
"""Record a fixed-interval low-resolution sequence for the V3 field shadow audit.

This is a standalone audit recorder. It refuses to run while pollipi.service is
active, does not execute V1/V3, and does not enable live adaptive capture.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

FRAME_SCHEMA = "pollipi-latent-disturbance-v3-field-frame-v1"
MANIFEST_SCHEMA = "pollipi-latent-disturbance-v3-field-collection-v1"
WIDTH = 640
HEIGHT = 360
WINDOW_LENGTH = 9
TEMPORAL_RANK = 3


def parse_roi(text: str) -> tuple[int, int, int, int]:
    try:
        vals = tuple(int(x.strip()) for x in text.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ROI must be x0,y0,x1,y1 integers") from exc
    if len(vals) != 4:
        raise argparse.ArgumentTypeError("ROI must contain exactly four integers")
    x0, y0, x1, y1 = vals
    if not (0 <= x0 < x1 <= WIDTH and 0 <= y0 < y1 <= HEIGHT):
        raise argparse.ArgumentTypeError(f"ROI must lie inside {WIDTH}x{HEIGHT} and have positive area")
    return vals


def service_is_active() -> bool:
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", "--quiet", "pollipi.service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        return False
    return proc.returncode == 0


def y_plane(frame):
    import numpy as np

    arr = np.asarray(frame)
    y_rows = arr.shape[0] * 2 // 3
    y = np.clip(arr[:y_rows], 0, 255).astype("uint8")
    if y.shape != (HEIGHT, WIDTH):
        raise RuntimeError(f"unexpected Y plane shape {y.shape}; expected {(HEIGHT, WIDTH)}")
    return y


def write_pgm(y, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"P5\n{WIDTH} {HEIGHT}\n255\n".encode("ascii")
    with path.open("wb") as f:
        f.write(header)
        f.write(y.tobytes(order="C"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--collection-id", required=True)
    p.add_argument("--prospective-role", choices=("development", "heldout"), required=True)
    p.add_argument("--recording-day", required=True)
    p.add_argument("--site-id", required=True)
    p.add_argument("--focal-scene-id", required=True)
    p.add_argument("--recording-block", required=True)
    p.add_argument("--comparison-session-id", required=True)
    p.add_argument("--plant-species", default="")
    p.add_argument("--primary-device-id", default=socket.gethostname())
    p.add_argument("--nuisance-reference-roi", type=parse_roi, required=True)
    p.add_argument("--truth-reference-source-id", required=True)
    p.add_argument("--frame-count", type=int, required=True)
    p.add_argument("--probe-interval-sec", type=float, default=5.0)
    p.add_argument("--max-timing-error-sec", type=float, required=True)
    p.add_argument("--source-commit", default=os.getenv("POLLIPI_SOURCE_COMMIT", "unknown"))
    return p


def validate_args(args) -> None:
    if args.frame_count < WINDOW_LENGTH:
        raise SystemExit(f"--frame-count must be >= {WINDOW_LENGTH}")
    if args.probe_interval_sec < 1.0:
        raise SystemExit("--probe-interval-sec must be >= 1")
    if args.max_timing_error_sec < 0:
        raise SystemExit("--max-timing-error-sec must be >= 0")
    if not args.collection_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for c in args.collection_id):
        raise SystemExit("--collection-id may contain only letters, digits, '.', '_' and '-'")


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args)
    if service_is_active():
        raise SystemExit("pollipi.service is active; stop the service before V3 audit recording")

    out = args.output_dir.expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"output directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    frames_dir = out / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now().astimezone()
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "collection_id": args.collection_id,
        "prospective_role": args.prospective_role,
        "recording_day": args.recording_day,
        "site_id": args.site_id,
        "focal_scene_id": args.focal_scene_id,
        "recording_block": args.recording_block,
        "comparison_session_id": args.comparison_session_id,
        "primary_device_id": args.primary_device_id,
        "plant_species": args.plant_species,
        "frame_width": WIDTH,
        "frame_height": HEIGHT,
        "frame_count": args.frame_count,
        "probe_interval_sec": args.probe_interval_sec,
        "max_timing_error_sec": args.max_timing_error_sec,
        "window_length": WINDOW_LENGTH,
        "temporal_rank": TEMPORAL_RANK,
        "nuisance_reference_mode": "within_frame_roi",
        "nuisance_reference_roi": list(args.nuisance_reference_roi),
        "nuisance_reference_target_free_expected": True,
        "truth_reference_source_id": args.truth_reference_source_id,
        "truth_reference_expected": True,
        "truth_reference_recorded": False,
        "live_adaptive_actions": False,
        "algorithm_scoring_during_collection": False,
        "source_commit": args.source_commit,
        "started_at": started.isoformat(timespec="seconds"),
        "governance_note": (
            "truth_reference_recorded stays false until an operator verifies that the independent truth stream "
            "was actually captured and archived. V3/V1 are not executed during collection."
        ),
    }
    (out / "collection_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    from picamera2 import Picamera2  # type: ignore

    cam = Picamera2()
    ledger_path = out / "v3_shadow_frames.csv"
    fieldnames = [
        "schema_version", "collection_id", "frame_index", "captured_at", "monotonic_sec",
        "filename", "sha256", "width", "height",
    ]

    try:
        cam.configure(cam.create_still_configuration(lores={"size": (WIDTH, HEIGHT), "format": "YUV420"}))
        cam.start()
        time.sleep(2.0)
        with ledger_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            next_due = time.monotonic()
            for i in range(args.frame_count):
                now = time.monotonic()
                if now < next_due:
                    time.sleep(next_due - now)
                captured_mono = time.monotonic()
                captured_at = datetime.now().astimezone()
                frame = cam.capture_array("lores")
                y = y_plane(frame)
                rel = Path("frames") / f"probe_{i:06d}.pgm"
                path = out / rel
                write_pgm(y, path)
                writer.writerow({
                    "schema_version": FRAME_SCHEMA,
                    "collection_id": args.collection_id,
                    "frame_index": i,
                    "captured_at": captured_at.isoformat(timespec="milliseconds"),
                    "monotonic_sec": f"{captured_mono:.9f}",
                    "filename": rel.as_posix(),
                    "sha256": sha256_file(path),
                    "width": WIDTH,
                    "height": HEIGHT,
                })
                f.flush()
                next_due += args.probe_interval_sec
    finally:
        try:
            cam.stop()
        finally:
            cam.close()

    finished = datetime.now().astimezone()
    manifest["finished_at"] = finished.isoformat(timespec="seconds")
    manifest["recorded_frame_count"] = args.frame_count
    (out / "collection_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(out)


if __name__ == "__main__":
    main()
