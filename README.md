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
→ candidate event
→ human review
→ insect / noise / unclear
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
→ stronger insect-like candidate

low tracking score + image change
→ lower confidence candidate / review priority only

tracking lost or large ROI shift
→ do not save supplemental event JPEG
→ keep scheduled timelapse image
→ log candidate_reason = tracking_lost or flower_or_camera_motion
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

Place the application files under:

```text
~/pollipi_timelapse/
```

At minimum:

```text
pollipi_api_server.py
install.sh
setup_device.sh
web/
```

---

## Deploy from Windows

Example PowerShell deployment:

```powershell
$env:POLLIPI_DEPLOY_PASSWORD = "your_pi_password"
.\deploy_pollipi_pi.ps1 -HostName pollipi1.local -User pi -Preset module3-wide -DeviceId pollipi1 -InstallDependencies
```

Manual copy:

```bash
ssh pi@pollipi1.local "mkdir -p ~/pollipi_timelapse"
scp pollipi_api_server.py install.sh setup_device.sh pi@pollipi1.local:~/pollipi_timelapse/
scp -r web pi@pollipi1.local:~/pollipi_timelapse/
ssh pi@pollipi1.local "bash ~/pollipi_timelapse/install.sh"
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
```

The current design discussion is tracked mainly in GitHub issues:

```text
#1 candidate-first review and ROI tracking quality
#2 selectable deletion / cleanup UI
#3 iPad Event Review robustness
#8 consolidated method design and adaptive timelapse scheduler
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
