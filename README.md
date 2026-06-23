# PolliPi Field Observer

PolliPi is a **local-first Raspberry Pi timelapse system** for flower-visitor observation.

It is not a motion-triggered camera, an ML training platform, or an automatic pollinator classifier.

```text
scheduled timelapse images
+ whole-frame overlapping mesh analysis
+ explainable three-state motion decision
+ shadow-mode metadata logging
```

The Raspberry Pi keeps capturing autonomously when the iPad or field router disconnects. The iPad is a lightweight control and inspection console.

## What is active now

### Primary field record

Every scheduled timelapse image is the scientific record.

- No image-per-motion-event stream.
- No candidate-event review queue.
- No active ML prediction or model training.
- No manual flower ROI or ROI tracking.
- A mesh decision is **not** a confirmed pollinator visit.

Confirmed visitation is assessed later from the scheduled images, with variable sampling effort considered when adaptive intervals are eventually enabled.

### Current decision states

| State | Interpretation | Current behaviour |
| --- | --- | --- |
| `no_activity` | activity below the mesh threshold | record scheduled image |
| `environmental_noise` | broad/global change, e.g. wind, shadow, shake | record scheduled image |
| `uncertain_local_activity` | local but ambiguous signal | record scheduled image |
| `strong_visitation_candidate` | compact local motion agreeing across offset meshes | record scheduled image; log the shorter interval that would be used later |

**Live adaptive interval control is disabled.** PolliPi currently operates in shadow mode: it logs the decision and the hypothetical next interval but keeps the configured scheduled interval unchanged.

## Analysis design

The shared analysis package is `packages/analysis`.

```text
frame pair
→ optional small global registration / brightness normalization
→ residual image
→ rectangular mesh + half-cell offset mesh
→ explainable features
→ three-state rule decision
→ shadow-mode interval plan
```

The working baseline uses rectangular meshes with a half-cell offset. A hexagonal mesh exists only for comparison and is not the active baseline.

Detailed method: [ADAPTIVE_TIMELAPSE_METHOD.md](ADAPTIVE_TIMELAPSE_METHOD.md)

Shadow log fields: [docs/SHADOW_MODE_LOGGING_CONTRACT.md](docs/SHADOW_MODE_LOGGING_CONTRACT.md)

## Repository layout

```text
packages/
  analysis/     Pure shared mesh analysis, policy, shadow runner, simulation
  server/       Raspberry Pi FastAPI runtime
  web/          iPad PWA
  contracts/    Shared browser/API contracts during migration

dist/           Generated deployable server artifact (pollipi_api_server.py)
tools/          Fleet deploy (pollipi_fleet_deploy.py) + pollipi.service.template
docs/           Deployment and design docs (DEPLOY_TO_PI.md, FIELD_FLEET_DEPLOYMENT.md)
```

New development belongs in `packages/`. The deployable server is the generated
`dist/pollipi_api_server.py` (built from `packages/server`); deploy it with
`tools/pollipi_fleet_deploy.py` per [docs/DEPLOY_TO_PI.md](docs/DEPLOY_TO_PI.md).
The original root-level single-file server and `web/` assets have been removed now
that all devices run the packaged artifact.

## Active API

```text
/device
/status
/start
/stop
/latest
/preview
/mjpeg
/images
```

`/mjpeg` is explicit and must not auto-open from the multi-device list. Normal operation is status-first; use one selected live viewer only after stability validation.

Retired active API surfaces:

```text
/events
/training/*
/roi/*
/compat/events
/compat/training/*
/compat/roi/*
```

## Development

### Python analysis and server tests

Use Python 3.11 or later. For Linux/WSL, create a virtual environment and install both packages with server development dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e packages/analysis -e "packages/server[dev]"

export POLLIPI_FAKE_CAMERA=1
python -m pytest packages/analysis/tests packages/server/tests -q
```

`POLLIPI_FAKE_CAMERA=1` tests the Python/API/runtime path without Picamera2 hardware.

### iPad web app

```bash
pnpm install
pnpm check:web
pnpm build:web
```

### Build the Pi server artifact

```bash
pnpm build:server
```

The generated deployment artifact is:

```text
dist/pollipi_api_server.py
```

Run a fake-camera smoke server locally:

```bash
POLLIPI_FAKE_CAMERA=1 POLLIPI_IMAGE_DIR="$(mktemp -d)" \
  python -m uvicorn --app-dir dist pollipi_api_server:app --host 127.0.0.1 --port 8000
```

## Field operation

1. Power the Raspberry Pi and camera.
2. Connect iPad and Pi to the private field network.
3. Register/select a device in the iPad PWA.
4. Set the scheduled interval and optional min/max interval for shadow planning.
5. Start recording.
6. Leave the Pi to capture autonomously.
7. Inspect scheduled images and shadow metadata later.

For multi-Pi work, use DHCP reservations on the field router rather than Pi-side fixed IP addresses. The normal iPad list should fetch lightweight status only; do not open five MJPEG streams.

## Validation status

Implemented:

- pure non-ML mesh analysis;
- three-state policy;
- deterministic synthetic simulation;
- shadow-mode decision logging;
- scheduled-image-only runtime;
- no active ROI, training, event review, or candidate image capture routes.

Still required before live adaptive timing is enabled:

- real fixed-interval Pi image sequences;
- manual comparison between visible insects and shadow decisions;
- false-positive / missed-signal assessment;
- calibration of thresholds for the actual field camera, flower, wind, and illumination conditions.

## Security and networking

Set `POLLIPI_DEVICE_SECRET` only when coordinator-to-Pi endpoints need protection. Keep the Pi API on a private LAN, VPN, or private overlay network; do not expose it directly to the public internet. A shared secret alone is not a substitute for TLS or a private network.
