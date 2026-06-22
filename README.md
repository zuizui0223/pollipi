# PolliPi Field Observer

PolliPi is a Raspberry Pi + iPad field camera workflow for flower-visitor monitoring.

It is **not** primarily a motion-triggered camera. The main design is:

```text
fixed-effort timelapse baseline
+ ROI-local candidate evidence
+ human-reviewed insect / noise / unclear labels
+ continuously adaptive timelapse scheduling
```

The system runs a FastAPI server on Raspberry Pi and serves an iPad-friendly PWA for camera setup, ROI selection, timelapse recording, candidate review, and data export.

Images are saved by default to:

```text
~/pollipi_timelapse/images
```

A different image directory can be set with:

```text
POLLIPI_IMAGE_DIR
```

---

## Repository source of truth

This branch is migrating PolliPi from the historical root-level layout into a monorepo.

| Area | Current root operation | Monorepo source of truth |
| --- | --- | --- |
| Raspberry Pi API server | `pollipi_api_server.py` at the repository root | `packages/server/src/visit_monitor_server` |
| iPad web app | root-level `web/` | `packages/web` |
| API/browser contracts | implicit in root Python + DOM code | `packages/contracts` plus typed web API helpers |
| Pi deployable server artifact | copied root `pollipi_api_server.py` | generated `dist/pollipi_api_server.py` |

During the transition, the root-level `pollipi_api_server.py` and `web/` are **not deleted**. They are treated as legacy / compatibility references so existing Pi deployments and behavior checks can continue while the package implementation becomes the maintained source.

After the migration is accepted:

- Backend feature work should happen in `packages/server`.
- Web UI feature work should happen in `packages/web`.
- Pi distribution should use a generated `dist/pollipi_api_server.py` artifact, not a manually edited root server file.
- Root-level files should become either compatibility shims, generated outputs, or archived legacy references. They should not regain source-of-truth status.

This PR does not intentionally change capture behavior, adaptive timelapse rules, ROI tracking semantics, or candidate review methodology. Those belong to separate issues such as #1 and #8.

---

## Monorepo developer workflow

Install workspace dependencies from the repository root:

```bash
pnpm install
```

Install the server Python package with test dependencies once per environment:

```bash
pip install -e "packages/server[dev]"
```

Run the packaged server in development:

```bash
pnpm dev:server
```

Run the server fake-camera smoke tests:

```bash
pnpm test:server
```

Equivalent direct command:

```bash
cd packages/server
POLLIPI_FAKE_CAMERA=1 pytest -q
```

Run the web type check and production build:

```bash
pnpm check:web
pnpm build:web
```

The web build output is produced under `packages/web/dist/`.

Build the Pi deployable single-file server artifact:

```bash
pnpm build:server
```

This writes:

```text
dist/pollipi_api_server.py
```

The generated file embeds the repository's `visit_monitor_server` package code. Third-party dependencies such as FastAPI, Uvicorn, Picamera2, and OpenCV still come from the Pi system packages or virtual environment.

A smoke check for the generated artifact can be run with:

```bash
POLLIPI_FAKE_CAMERA=1 POLLIPI_IMAGE_DIR="$(mktemp -d)" \
  python dist/pollipi_api_server.py --host 127.0.0.1 --port 8000
```

Or with Uvicorn:

```bash
POLLIPI_FAKE_CAMERA=1 POLLIPI_IMAGE_DIR="$(mktemp -d)" \
  python -m uvicorn --app-dir dist pollipi_api_server:app --host 127.0.0.1 --port 8000
```

---

## Current research framing

PolliPi should be evaluated against ordinary fixed-interval timelapse, not framed as a pure motion-trigger camera.

The core question is:

```text
Can an adaptive timelapse workflow preserve comparable baseline recording while reducing missed visits, unnecessary review load, and storage waste?
```

The fixed timelapse record remains the scientific baseline. Candidate detection and adaptive scheduling are used to improve sampling density and review priority, not to replace baseline observations.

---

## Core data logic

### Baseline images

Scheduled timelapse images are always the main comparable record.

```text
scheduled image = fixed-effort baseline observation
```

These images should not be suppressed by motion detection, ML, sensor readings, or ROI tracking failure.

### Candidate evidence

ROI-local image changes are treated as candidate evidence, not biological truth.

```text
ROI-local change
-> candidate event
-> human review
-> insect / noise / unclear
```

Automatic detection should answer:

```text
Did something happen near the focal flower/head that is worth reviewing?
```

Manual review should answer:

```text
Was it actually an insect/visit, noise, or unclear?
```

### Review labels vs training labels

Do not treat automatic `positive` as confirmed insect presence.

Use this separation:

```text
review_label:
  insect
  noise
  unclear

training_label:
  positive  <- review_label=insect
  negative  <- review_label=noise
  excluded  <- review_label=unclear
```

Training should use manually reviewed labels by default. Auto labels and field ML predictions should not silently enter the training set.

---

## Recording modes

PolliPi may contain several modes for comparison and development, but their scientific roles differ.

| Mode | Role |
| --- | --- |
| Fixed timelapse | Main baseline. Constant observation effort. |
| Whole-frame image difference / motion trigger | Noisy comparison mode, not main workflow. |
| ROI-local candidate detection | Candidate evidence around focal flower/head. |
| Hybrid timelapse + candidate evidence | Baseline images plus rate-limited supplemental candidates. |
| Adaptive timelapse | Target workflow: interval changes according to recent candidate activity and noise. |

The preferred field workflow is:

```text
fixed timelapse baseline
+ ROI-local candidate evidence
+ human review
+ adaptive interval support
```

---

## Continuously adaptive timelapse design

The target adaptive scheduler should not be limited to only three states such as `QUIET / WATCH / ACTIVE`.

Instead, it should compute an activity score and map it continuously to a sampling interval:

```text
activity_score = 0.0 -> about 60 sec
activity_score = 0.3 -> about 45 sec
activity_score = 0.5 -> about 30 sec
activity_score = 0.8 -> about 15 sec
activity_score = 1.0 -> about 5 sec
```

The score should combine:

```text
recent ROI-local candidate frequency
short-term insect-like burst signal
candidate quality
noise-like candidate penalty
weak-change / brightness-change penalty
reviewed-label memory
time-of-day/site memory
power/storage guardrails
```

A simple implementation sketch:

```python
activity = (
    0.50 * insect_like_rate_10min
    + 0.25 * insect_like_rate_2min
    + 0.15 * time_of_day_prior
    + 0.10 * reviewed_memory_score
    - 0.40 * noise_like_rate_10min
    - 0.20 * weak_change_rate_10min
)

activity_score = clamp(activity, 0.0, 1.0)
target_interval = max_interval_sec - activity_score * (max_interval_sec - min_interval_sec)
new_interval = 0.7 * current_interval + 0.3 * target_interval
```

Important rule:

```text
Adaptive scheduling changes sampling density.
It must not erase the fixed-effort baseline record.
```

Recommended log fields:

```text
adaptive_interval_sec
target_interval_sec
activity_score
adaptive_reason
candidate_rate_2min
candidate_rate_10min
insect_like_rate_2min
insect_like_rate_10min
noise_like_rate_10min
weak_change_rate_10min
reviewed_memory_score
time_of_day_prior
interval_smoothing_alpha
```

---

## ROI tracking principle

ROI tracking follows the focal flower/head, not the insect.

The current principle is:

```text
1. User selects a flower/head ROI.
2. The ROI appearance is saved as a template.
3. Later frames search near the previous ROI.
4. If a similar patch is found, the ROI is shifted.
5. Candidate detection is performed inside the updated ROI.
```

ROI tracking quality should affect candidate interpretation.

Use fields such as:

```text
roi_tracking_success
roi_tracking_score
roi_shift_x
roi_shift_y
roi_shift_distance
roi_tracking_status
```

Suggested interpretation:

```text
high tracking score + local visitor-like change
-> stronger insect-like candidate

low tracking score + image change
-> lower confidence candidate / review priority only

tracking lost or large ROI shift
-> do not save supplemental event JPEG
-> keep scheduled timelapse image
-> log candidate_reason = tracking_lost or flower_or_camera_motion
```

This prevents flower movement, camera movement, or tracking failure from being treated as insect activity.

---

## Field workflow

1. Set up the Raspberry Pi and camera.
2. Connect iPad to the Pi Wi-Fi or shared field network.
3. Open:

```text
http://pollipi.local:8000/app/
```

4. Select the focal flower/head ROI in the preview.
5. Start fixed or hybrid/adaptive recording.
6. Let the Pi continue recording autonomously even if iPad disconnects.
7. Reconnect later to review candidate events and export logs/images.

For one-camera field use, a Pi-hosted Wi-Fi network is usually simplest. For multi-camera comparison, all Pi devices and the iPad should be on the same field network.

---

## Device authentication

PolliPi supports optional per-device shared-secret authentication for coordinator-to-Pi traffic.

Local direct field use:

- Leave `POLLIPI_DEVICE_SECRET` unset.
- The Pi API keeps the historical local-network behavior.
- This is suitable for one Pi and one iPad on a private field Wi-Fi where the Pi is not exposed outside the local network.

Coordinator-managed use:

- Set the same secret on the Pi and in the coordinator device record.
- The Pi requires `X-Pollipi-Device-Secret` only when `POLLIPI_DEVICE_SECRET` is set.
- The coordinator stores `device_secret` and `PiClient` sends it as `X-Pollipi-Device-Secret` on proxied Pi requests.
- Device API responses never include the stored secret.

Protected Pi endpoints include:

```text
/start
/stop
/mjpeg
/images...
/events...
/exports...
/training...
```

Unprotected discovery/status endpoints include:

```text
/device
/status
/system
/preview
/latest
```

Set the secret on the Pi service environment:

```ini
Environment=POLLIPI_DEVICE_SECRET=change-this-long-random-secret
```

Or for a manual run:

```bash
POLLIPI_DEVICE_SECRET='change-this-long-random-secret' \
  .venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000
```

Coordinator registration can include:

```json
{
  "address": "pi@pollipi1",
  "base_url": "http://pollipi1.local:8000",
  "device_secret": "change-this-long-random-secret",
  "verify_connection": true
}
```

Remote deployment:

- Prefer VPN or private overlay networking such as Tailscale, WireGuard, or ZeroTier.
- If traffic crosses untrusted networks, use HTTPS or a tunnel. Plain HTTP exposes the shared secret and image data to anyone who can observe the network.
- A shared secret is a minimal control-plane protection, not a substitute for TLS, VPN, or a private tunnel.
- DDNS alone does not solve NAT/CGNAT reachability and does not encrypt traffic.

Short-term field-network decision for #10:

- Keep the Pi HTTP API reachable only on a private field LAN or private overlay network.
- Use `POLLIPI_DEVICE_SECRET` for coordinator-to-Pi control and streaming endpoints.
- Do not expose Pi ports directly to the public internet.
- Treat outbound WebSocket control from Pi to coordinator as future hardening, not required for the current field deployment issue.

---

## GL.iNet / field router operation

A small GL.iNet router can be the field network hub for multi-camera work:

```text
GL.iNet field router
  - pollipi1 192.168.8.101
  - pollipi2 192.168.8.102
  - pollipi3 192.168.8.103
  - iPad or coordinator laptop
```

Recommended setup:

1. Configure one private SSID for the field site.
2. Join every Raspberry Pi and the iPad/coordinator to that SSID.
3. Add DHCP reservations for each Pi so the addresses stay stable.
4. Open each Pi directly from the iPad for one-by-one operation, or register the fixed Pi URLs in the coordinator.
5. If remote access is needed, run Tailscale, WireGuard, or another private overlay on the router or coordinator instead of forwarding Pi ports.

Example coordinator device URLs:

```text
http://192.168.8.101:8000
http://192.168.8.102:8000
http://192.168.8.103:8000
```

For direct one-camera operation on a private router LAN, `POLLIPI_DEVICE_SECRET` can be left unset. For coordinator-managed or remote-overlay operation, set a long unique secret on each Pi and store the same value in the coordinator device record.

---

## Raspberry Pi setup

Confirm the camera works:

```bash
rpicam-hello
```

Install dependencies and create the runtime directory:

```bash
bash install.sh
```

Manual setup:

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-venv python3-fastapi python3-uvicorn
mkdir -p ~/pollipi_timelapse/images
cd ~/pollipi_timelapse
python3 -m venv --system-site-packages .venv
```

### Current root operation

Existing Pi deployments can continue to run the compatibility layout:

```text
~/pollipi_timelapse/
  pollipi_api_server.py
  install.sh
  setup_device.sh
  web/
```

Start command:

```bash
cd ~/pollipi_timelapse
.venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000
```

This path remains valid during the migration so field devices are not forced to switch immediately.

### Monorepo artifact operation

The target deployment flow is to build from `packages/server` and copy the generated artifact:

```bash
pnpm build:server
```

Then place the generated file on the Pi as:

```text
~/pollipi_timelapse/pollipi_api_server.py
```

The service can keep the same Uvicorn import path:

```bash
cd ~/pollipi_timelapse
.venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000
```

This preserves the Pi operational model while moving maintained backend source code to `packages/server`.

---

## Deploy from Windows

Current compatibility deployment still copies root files:

```powershell
$env:POLLIPI_DEPLOY_PASSWORD = "your_pi_password"
.\deploy_pollipi_pi.ps1 -HostName pollipi1.local -User pi -Preset module3-wide -DeviceId pollipi1 -InstallDependencies
```

The monorepo target is:

1. Build `dist/pollipi_api_server.py` from `packages/server`.
2. Build the PWA with `pnpm build:web`.
3. Copy `dist/pollipi_api_server.py` to the Pi as `~/pollipi_timelapse/pollipi_api_server.py`.
4. Copy `packages/web/dist/` to the Pi web asset location used by the packaged server.
5. Restart `pollipi.service` and run `/device`, `/status`, `/start`, `/images`, `/latest`, and `/stop` smoke checks.

Manual compatibility copy:

```bash
ssh pi@pollipi1.local "mkdir -p ~/pollipi_timelapse"
scp pollipi_api_server.py install.sh setup_device.sh pi@pollipi1.local:~/pollipi_timelapse/
scp -r web pi@pollipi1.local:~/pollipi_timelapse/
ssh pi@pollipi1.local "bash ~/pollipi_timelapse/install.sh"
```

Manual artifact copy after building:

```bash
ssh pi@pollipi1.local "mkdir -p ~/pollipi_timelapse"
scp dist/pollipi_api_server.py pi@pollipi1.local:~/pollipi_timelapse/pollipi_api_server.py
scp -r packages/web/dist pi@pollipi1.local:~/pollipi_timelapse/web
ssh pi@pollipi1.local "sudo systemctl restart pollipi.service"
```

---

## Start the server

Camera Module 3 example:

```bash
cd ~/pollipi_timelapse
POLLIPI_DEVICE_NAME='Site 01' POLLIPI_CAMERA_LABEL='Module 3 Wide' POLLIPI_CAMERA_MODEL='imx708_wide' \
  .venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000
```

AI Camera example:

```bash
cd ~/pollipi_timelapse
POLLIPI_DEVICE_NAME='Site 02' POLLIPI_CAMERA_LABEL='AI Camera' POLLIPI_CAMERA_MODEL='imx500' \
  .venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000
```

---

## systemd autonomous operation

Use `setup_device.sh`:

```bash
bash ~/pollipi_timelapse/setup_device.sh pollipi1
```

Or create a service manually:

```bash
sudo tee /etc/systemd/system/pollipi.service >/dev/null <<'EOF'
[Unit]
Description=PolliPi Field Observer API
After=network-online.target
Wants=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/pollipi_timelapse
ExecStart=/home/pi/pollipi_timelapse/.venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 3
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now pollipi.service
```

When autonomous operation is enabled from the app, settings are stored in:

```text
~/pollipi_timelapse/autonomous_run.json
```

After reboot, the Pi can resume recording.

---

## Pi as a field Wi-Fi hotspot

On Raspberry Pi OS Bookworm or later:

```bash
sudo nmcli device wifi hotspot ssid PolliPi-site01 password 'change-this-password'
```

Then connect the iPad to `PolliPi-site01` and open:

```text
http://<Pi address>:8000/app/
```

For multi-camera synchronized operation, use one shared field network rather than separate hotspots for every Pi.

---

## API examples

Start ordinary timelapse:

```bash
curl -X POST http://pollipi1.local:8000/start \
  -H "Content-Type: application/json" \
  -d '{"interval_sec": 30, "autonomous_mode": true}'
```

Start with a configured device secret:

```bash
curl -X POST http://pollipi1.local:8000/start \
  -H "Content-Type: application/json" \
  -H "X-Pollipi-Device-Secret: change-this-long-random-secret" \
  -d '{"interval_sec": 30, "autonomous_mode": true}'
```

Start hybrid baseline + candidate evidence:

```bash
curl -X POST http://pollipi1.local:8000/start \
  -H "Content-Type: application/json" \
  -d '{"interval_sec": 30, "hybrid_mode": true, "autonomous_mode": true, "detection_interval_sec": 3}'
```

Start legacy motion-trigger comparison mode:

```bash
curl -X POST http://pollipi1.local:8000/start \
  -H "Content-Type: application/json" \
  -d '{"interval_sec": 60, "motion_trigger_mode": true, "autonomous_mode": true, "detection_interval_sec": 3}'
```

Check status:

```bash
curl http://pollipi1.local:8000/status
```

Preview:

```bash
curl http://pollipi1.local:8000/preview --output preview.jpg
```

Latest image:

```bash
curl http://pollipi1.local:8000/latest --output latest.jpg
```

Stop recording:

```bash
curl -X POST http://pollipi1.local:8000/stop
```

---

## Data files

Common runtime outputs include:

```text
images/*.jpg
observation_events.csv
event_log.csv
adaptive_metrics.csv
image_labels.csv
```

Scientific interpretation should prioritize:

```text
scheduled / scheduled_event images
manual review labels
candidate metrics
ROI and tracking metadata
```

Supplemental event images are useful for review efficiency, but they are not by themselves confirmed biological events.

---

## What not to do

Do not interpret auto labels as final insect records.

Do not train ML on unreviewed auto labels by default.

Do not let adaptive scheduling suppress baseline scheduled images.

Do not treat whole-frame image difference as the main PolliPi method.

Do not add YOLO or species identification before the candidate/review pipeline is stable.

---

## Related project documents

```text
MASTER_SPEC.md      conceptual specification
TASKS.md            implementation tasks
HANDOFF.md          handoff notes
DECISIONS.md        design decisions
CHANGELOG_AI.md     AI-assisted change log
FIELD_METHOD_ROADMAP.md field-method roadmap
MIGRATION_PLAN.md   monorepo migration and artifact plan
```

The current design discussion is tracked mainly in GitHub issues:

```text
#1 candidate-first review and ROI tracking quality
#2 selectable deletion / cleanup UI
#3 iPad Event Review robustness
#8 consolidated method design and adaptive timelapse scheduler
#10 Pi-to-coordinator device authentication
#11 monorepo migration tracking
```

---

## Short method wording

```text
PolliPi preserves fixed-effort timelapse as the baseline record, while ROI-local candidate evidence and human-reviewed labels are used to prioritize review and continuously adjust sampling interval.
```

Japanese wording:

```text
PolliPiでは、定間隔タイムラプスを基準記録として維持しつつ、焦点花ROI内の候補頻度・候補品質・ノイズ指標に応じて撮影間隔を連続的に変化させる可変間隔タイムラプスを採用する。
```
