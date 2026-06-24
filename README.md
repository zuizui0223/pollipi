# PolliPi Field Observer

PolliPi is a **local-first Raspberry Pi timelapse system** for flower-visitor observation.

```text
scheduled high-resolution JPEG timelapse
+ low-resolution probe analysis
+ whole-frame overlapping mesh decisions
+ shadow-mode metadata logging
```

It is **not** a pure motion-triggered camera, a field-time ML training system, or an automatic pollinator classifier. The scheduled JPEG sequence is the scientific record; mesh output is supporting metadata.

> 日本語の実際の操作手順: [現行運用ガイド](docs/OPERATION_GUIDE_JA.md)

## Current operating model

- Each Pi captures autonomously after a session has been started.
- The iPad is a direct local control and inspection console.
- A coordinator / central server is **not required** for normal laboratory or field-LAN operation.
- The field router only needs to place the iPad and Pis on the same private Wi-Fi LAN. WAN, SIM, and cloud access are unnecessary.
- Current deployment has **live adaptive interval control disabled**. Shadow mode records a hypothetical next interval but preserves the configured JPEG interval.

## What is active now

### Primary field record

Every high-resolution scheduled timelapse image is retained as the primary record.

- No image-per-motion-event stream.
- No active candidate-event review queue.
- No active ML prediction or model training.
- No manual flower ROI or ROI tracking.
- A mesh decision is **not** a confirmed pollinator visit.

The default runtime uses a low-resolution probe every 5 seconds without saving a probe JPEG. The high-resolution JPEG interval remains the configured scheduled interval, normally **30 seconds**.

### Mesh decisions and shadow mode

The active analysis evaluates whole-frame rectangular meshes plus a half-cell offset mesh. It reports one of these observation states:

| State | Meaning | Current effect |
| --- | --- | --- |
| `no_activity` | activity is below the mesh threshold | save the scheduled JPEG normally |
| `environmental_noise` | broad/global change such as wind, shadow, or shake | save the scheduled JPEG normally |
| `uncertain_local_activity` | local but ambiguous motion | save the scheduled JPEG normally |
| `strong_visitation_candidate` | compact local motion with offset-mesh agreement | save the scheduled JPEG normally; log the shorter interval that could be used later |

`Would-be mode` and `Would-be interval` are advisory shadow outputs. They do **not** change actual capture timing while `live_adaptive_enabled=false`.

### Policy profiles

The iPad console currently offers:

- `three_stage_default_v1` — use this for initial fixed-interval field sessions.
- `three_stage_sensitive_v1` — comparison profile; use only after collecting fixed-interval data and reviewing shadow outputs.

Both profiles remain shadow-only. They are not field-validated visit classifiers.

## iPad quick operation

1. Connect the iPad and every Pi to the same private LAN.
2. Open one Pi in Safari at `http://<PI-IP>:8000/app/`.
3. Add the page to the home screen if desired.
4. Under **Add Raspberry Pi**, enter every other Pi's IP address, for example `192.168.11.18`.
5. Confirm all device cards are online.
6. Set `30 sec baseline`, choose `three_stage_default_v1`, and enable **Resume autonomously after Pi restart** when the session must survive Pi reboot.
7. Select **Start all**.
8. Confirm every card shows `capturing`, `High-res interval = 30 sec`, and `Shadow only = on`.
9. Confirm `last capture` advances at least twice before leaving the system unattended.

When a Pi is stopped, its card may show a low-resolution MJPEG framing preview. During capture, PolliPi releases the preview path to avoid camera contention and displays `Capturing` instead.

## Field router operation

A field router is used as a local Wi-Fi access point and DHCP server, not as an internet gateway.

- Set a fixed SSID and password.
- Keep DHCP enabled.
- Disable guest-network isolation / AP isolation / client isolation.
- Assign DHCP reservations for all five Pis.
- Prefer router-side DHCP reservations over Pi-side static IP configuration.
- On a separate field LAN such as `192.168.8.0/24`, reserve addresses like `.11` through `.15` for the Pis.

The detailed field readiness and disconnect/reboot tests are in [FIELD_READINESS_CHECKLIST.md](docs/FIELD_READINESS_CHECKLIST.md).

## Repository layout

```text
packages/
  analysis/     Pure shared mesh analysis, policy, shadow runner, simulation
  server/       Raspberry Pi FastAPI runtime
  web/          iPad PWA
  contracts/    Shared browser/API contracts

dist/           Generated deployable server artifact (pollipi_api_server.py)
tools/          Fleet deploy utility and service template
docs/           Operation, deployment, and field-readiness documents
```

New development belongs in `packages/`. The deployment artifact is generated from `packages/server` into `dist/pollipi_api_server.py`.

## Build and deploy

### Build artifacts on Windows, macOS, Linux, or WSL

```bash
pnpm install
pnpm check:web
pnpm build:artifacts
```

`build:artifacts` intentionally builds the web app first and the server artifact second, so the packaged server embeds the same web build ID that will be deployed. The server build no longer relies on POSIX-only `PYTHONPATH=...` syntax.

### Full fleet deployment

Use `tools/pollipi_fleet_deploy.py` as the only deployment authority. Always dry-run first.

```powershell
python tools\pollipi_fleet_deploy.py --config tools\fleet.local.json
```

After reviewing the resolved hosts, artifact commit, web build ID, and rollback plan:

```powershell
python tools\pollipi_fleet_deploy.py `
  --config tools\fleet.local.json `
  --execute `
  --confirm-live-deploy
```

A full deployment backs up the current server and web build, uploads both artifacts, restarts the configured service, then verifies the deployed commit and web build ID. It stops at the first failed Pi and rolls back that Pi when a post-upload step fails.

For a web-only change, use the explicit web-only mode only when the server artifact is intentionally unchanged. See [DEPLOY_TO_PI.md](docs/DEPLOY_TO_PI.md).

## Active API

```text
/device
/status
/policy-profiles
/start
/stop
/latest
/preview
/mjpeg
/images
```

Retired active surfaces include `/events`, `/training/*`, and `/roi/*`.

## Field readiness before data collection

A Pi is not field-ready merely because its card is visible on the iPad. Each Pi must pass:

1. fixed-interval capture verification;
2. iPad disconnect verification;
3. field-router disconnect/reconnect verification;
4. Pi reboot plus autonomous-resume verification;
5. storage, clock, image, and shadow-log verification.

See [FIELD_READINESS_CHECKLIST.md](docs/FIELD_READINESS_CHECKLIST.md) for the exact go/no-go checklist.

## Validation status

Implemented:

- pure non-ML mesh analysis;
- versioned policy profiles;
- scheduled high-resolution JPEG capture;
- 5-second low-resolution probes without saved probe JPEGs;
- shadow-mode decision logging;
- direct iPad-to-Pi local-LAN control;
- packaged artifact and safe fleet deployment flow.

Still required before enabling live adaptive timing:

- real fixed-interval Pi image sequences;
- manual comparison between visible insects and shadow decisions;
- false-positive and missed-signal assessment;
- threshold calibration for actual flower, wind, illumination, and camera conditions.

## Security and networking

Keep the Pi API on a private trusted LAN. Do not expose port 8000 directly to the public internet.

`POLLIPI_DEVICE_SECRET` is intended for a future coordinator-managed or remote-access deployment. It is not needed for the current direct iPad-to-Pi field LAN workflow. A shared secret is not a substitute for TLS, VPN, or a private network.
