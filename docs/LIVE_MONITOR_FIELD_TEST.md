# Live monitor: deploy and field test (5 units)

## What changed

The web monitor is now an **in-card live viewfinder**. Clicking **Monitor** shows
the live camera view inside the device card (no more jumping to a separate page),
so you can check framing before starting capture.

On the device, the monitor producer now opens a dedicated low-res preview camera
**while the timelapse is idle**, then releases it the moment capture starts (the
capture loop owns the sensor; access is serialized by the camera lock). While
capturing, the card shows the latest scheduled frame.

## Units

| name    | ssh target                | base URL                  |
|---------|---------------------------|---------------------------|
| zuizui  | `zuizui0223@zuizui.local` | `http://zuizui.local:8000`  |
| zuizui2 | `zuizui0223@zuizui2.local`| `http://zuizui2.local:8000` |
| zuizui3 | `zuizui0223@zuizui3.local`| `http://zuizui3.local:8000` |
| zuizui4 | `zuizui0223@zuizui4.local`| `http://zuizui4.local:8000` |
| zuizui5 | `zuizui0223@zuizui5.local`| `http://zuizui5.local:8000` |

Fleet config: `tools/fleet.zuizui.json`.

> Run all of the commands below from a machine **on the same LAN** as the Pis.

## 1. Build artifacts

```bash
# Web UI
pnpm --filter @visit-monitor/web build      # outputs packages/web/dist
# Server single-file artifact -> dist/pollipi_api_server.py
python -m visit_monitor_server.distribution.bundle_single_file   # or your usual build step
```

## 2. Deploy

Dry-run first (no changes), then execute:

```bash
python tools/pollipi_fleet_deploy.py --config tools/fleet.zuizui.json
python tools/pollipi_fleet_deploy.py --config tools/fleet.zuizui.json --execute --confirm-live-deploy
```

Single unit instead of the whole fleet:

```bash
PI_HOST=zuizui.local PI_USER=zuizui0223 ./scripts/deploy_pi.sh
```

## 3. Verify the live monitor

```bash
python tools/check_live_monitor.py \
  http://zuizui.local:8000 http://zuizui2.local:8000 http://zuizui3.local:8000 \
  http://zuizui4.local:8000 http://zuizui5.local:8000
```

Each unit should report `OK` for `/device`, `/status`, and `live monitor /mjpeg`.
Exit code is non-zero if any unit fails. Add `--secret <value>` if the devices
set `POLLIPI_DEVICE_SECRET`.

## 4. Manual UI check

1. Open the web console and add each unit (e.g. `zuizui0223@zuizui`).
2. On a card, tap **Monitor** *before* starting capture — a live view with a
   **LIVE** badge should appear in the card.
3. Tap **Start**; the live preview is released and the card shows scheduled
   frames. Tap **Stop**, then **Monitor** again to confirm the live view returns.

If a unit shows "No live signal", check the camera cable/connector and that the
service restarted cleanly (`systemctl status pollipi.service` on the Pi).
