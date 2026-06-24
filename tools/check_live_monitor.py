#!/usr/bin/env python3
"""Field smoke test for the in-card live monitor on one or more PolliPi units.

For each base URL it checks, over the LAN:

  1. ``GET /device``  -> 200 with a device_id
  2. ``GET /status``  -> 200 (reports whether capture is running)
  3. ``GET /mjpeg``   -> a live JPEG frame arrives within a few seconds

Step 3 is the new behaviour: the monitor now opens a live preview even when the
device is idle (nothing captured yet), so you can frame the shot before starting.

Run it from a machine on the same LAN as the Raspberry Pi units (it cannot be
run from outside the field network):

    python tools/check_live_monitor.py \
        http://zuizui.local:8000 http://zuizui2.local:8000 \
        http://zuizui3.local:8000 http://zuizui4.local:8000 http://zuizui5.local:8000

Add ``--secret <value>`` if the devices set POLLIPI_DEVICE_SECRET.
Exit code is non-zero if any device fails, so it is CI/script friendly.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

#: JPEG start-of-image marker. Its presence in the stream proves a real frame.
JPEG_SOI = b"\xff\xd8\xff"


def contains_jpeg_frame(buffer: bytes) -> bool:
    """True if *buffer* holds at least one multipart MJPEG JPEG frame."""
    return b"--frame" in buffer and JPEG_SOI in buffer


def _headers(secret: str | None) -> dict[str, str]:
    return {"X-Pollipi-Device-Secret": secret} if secret else {}


def check_json(base_url: str, endpoint: str, secret: str | None, timeout: float) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/{endpoint}"
    try:
        req = urllib.request.Request(url, headers=_headers(secret))
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(8192).decode("utf-8", errors="replace")
            if response.status != 200:
                return False, f"HTTP {response.status}"
            data = json.loads(body)
            return True, json.dumps(data, ensure_ascii=False)[:200]
    except Exception as exc:
        return False, str(exc)


def check_live_monitor(base_url: str, secret: str | None, deadline_sec: float) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/mjpeg"
    end = time.monotonic() + deadline_sec
    try:
        req = urllib.request.Request(url, headers=_headers(secret))
        response = urllib.request.urlopen(req, timeout=deadline_sec)
    except Exception as exc:
        return False, f"could not open /mjpeg: {exc}"

    buffer = b""
    try:
        while time.monotonic() < end and len(buffer) < 500_000:
            try:
                chunk = response.read(4096)
            except Exception:
                break
            if not chunk:
                break
            buffer += chunk
            if contains_jpeg_frame(buffer):
                return True, f"live JPEG frame received ({len(buffer)} bytes read)"
    finally:
        response.close()
    return False, f"no live JPEG frame within {deadline_sec:.0f}s ({len(buffer)} bytes read)"


def check_device(base_url: str, *, secret: str | None, mjpeg_timeout: float) -> bool:
    print(f"\n== {base_url} ==")
    ok = True
    for endpoint in ("device", "status"):
        passed, detail = check_json(base_url, endpoint, secret, timeout=8.0)
        ok = ok and passed
        print(f"  [{'OK ' if passed else 'FAIL'}] GET /{endpoint}: {detail}")
    passed, detail = check_live_monitor(base_url, secret, deadline_sec=mjpeg_timeout)
    ok = ok and passed
    print(f"  [{'OK ' if passed else 'FAIL'}] live monitor /mjpeg: {detail}")
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PolliPi live-monitor field smoke test")
    parser.add_argument("base_urls", nargs="+", help="device base URLs, e.g. http://zuizui.local:8000")
    parser.add_argument("--secret", default=None, help="POLLIPI_DEVICE_SECRET, if configured")
    parser.add_argument("--mjpeg-timeout", type=float, default=6.0, help="seconds to wait for a live frame")
    args = parser.parse_args(argv)

    results = [
        check_device(url, secret=args.secret, mjpeg_timeout=args.mjpeg_timeout)
        for url in args.base_urls
    ]
    passed = sum(results)
    print(f"\n{passed}/{len(results)} device(s) passed.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
