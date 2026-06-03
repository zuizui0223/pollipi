# PolliPi Device Onboarding Guide

This document describes how to add a new Raspberry Pi camera unit to the PolliPi field observer system.

Use this when adding any new Pi — for example `pollipi2.local`, `pollipi3.local`, or any hostname you assign.

## 1. Decide the device role

Before setup, decide the hostname, device ID, and camera type.

Generic example fleet:

| Hostname | Camera | Role |
|---|---|---|
| `pollipi1.local` | Camera Module 3 Wide | standard daylight unit |
| `pollipi2.local` | Raspberry Pi AI Camera | AI Camera comparison / detection-test unit |
| `pollipi3.local` | Camera Module 3 NoIR Wide | NoIR / low-light / IR-capable unit |

You can use any hostname that is unique on your network. The device ID (used in filenames and logs) defaults to the hostname without `.local`.

Default rule:

- AI Camera: set `IS_AI_CAMERA=true`.
- NoIR Wide: set `IS_NOIR=true`.
- Module 3 Wide: set `IS_WIDE=true` and use `module3_wide_daylight` profile.

## 2. Confirm SSH access

From Windows PowerShell (replace `pi` with your username and `pollipi2.local` with the new hostname):

```powershell
ssh pi@pollipi2.local
```

If SSH does not work, first confirm:

- Pi is powered on.
- Pi is on the same network.
- hostname is correct.
- SSH is enabled.

## 3. Confirm camera hardware

On the Pi:

```bash
rpicam-hello --list-cameras
rpicam-hello --timeout 3000
```

Expected:

- Module 3 / Module 3 Wide should show an IMX708 camera.
- AI Camera should show the appropriate AI camera hardware.
- NoIR Wide is also IMX708-based but should be treated as NoIR/IR-capable in metadata.

Do not continue PolliPi setup until `rpicam-hello --timeout 3000` works.

## 4. Install or update PolliPi code

### Option A: install.sh on the Pi directly

Copy files to the Pi and run:

```bash
scp pollipi_api_server.py install.sh setup_device.sh pi@pollipi2.local:~/pollipi_timelapse/
ssh pi@pollipi2.local "bash ~/pollipi_timelapse/install.sh"
```

### Option B: git clone on the Pi

```bash
ssh pi@pollipi2.local
git clone https://github.com/YOUR_FORK/pollipi.git ~/pollipi_timelapse
bash ~/pollipi_timelapse/install.sh
```

### Option C: Windows deployment helper

From a Windows PC, the deployment helper copies source files, sets the camera profile, runs syntax checks, installs the service, and restarts PolliPi.

Standard daylight Module 3 Wide example for `pollipi2.local`:

```powershell
$env:POLLIPI_DEPLOY_PASSWORD = "your_pi_password"
.\deploy_pollipi_pi.ps1 -HostName pollipi2.local -User pi -Preset module3-wide -DeviceId pollipi2 -InstallDependencies
```

After the first deployment, `-InstallDependencies` can usually be omitted:

```powershell
$env:POLLIPI_DEPLOY_PASSWORD = "your_pi_password"
.\deploy_pollipi_pi.ps1 -HostName pollipi2.local -User pi -Preset module3-wide -DeviceId pollipi2
```

If `.local` name resolution is not working but the IP address is known:

```powershell
.\deploy_pollipi_pi.ps1 -HostName 192.168.1.25 -User pi -Preset module3-wide -DeviceId pollipi2
```

## 5. Configure device profile

The easiest way is to run `setup_device.sh` on the Pi — it writes the service and drop-in interactively.

To configure manually, create or edit the systemd drop-in file:

```bash
sudo mkdir -p /etc/systemd/system/pollipi.service.d
sudo nano /etc/systemd/system/pollipi.service.d/camera-profile.conf
```

### Module 3 Wide example: `pollipi2.local`

```ini
[Service]
Environment=POLLIPI_DEVICE_ID=pollipi2
Environment="POLLIPI_DEVICE_NAME=Site 2 Module 3 Wide"
Environment="POLLIPI_CAMERA_LABEL=Module 3 Wide"
Environment=POLLIPI_CAMERA_MODEL=imx708_wide
Environment=POLLIPI_CAMERA_PROFILE=module3_wide_daylight
Environment=POLLIPI_IS_AI_CAMERA=false
Environment=POLLIPI_IS_NOIR=false
Environment=POLLIPI_IS_WIDE=true
```

### AI Camera example: `pollipi-ai.local`

```ini
[Service]
Environment=POLLIPI_DEVICE_ID=pollipi-ai
Environment="POLLIPI_DEVICE_NAME=AI Camera Unit"
Environment="POLLIPI_CAMERA_LABEL=AI Camera"
Environment=POLLIPI_CAMERA_MODEL=imx500
Environment=POLLIPI_CAMERA_PROFILE=ai_camera_daylight
Environment=POLLIPI_IS_AI_CAMERA=true
Environment=POLLIPI_IS_NOIR=false
Environment=POLLIPI_IS_WIDE=false
```

Important:

- The default AI Camera model is not an insect classifier.
- Treat AI Camera output as comparison / detection-test metadata unless a validated insect model is used.

### NoIR Wide example: `pollipi-noir.local`

```ini
[Service]
Environment=POLLIPI_DEVICE_ID=pollipi-noir
Environment="POLLIPI_DEVICE_NAME=NoIR Wide Unit"
Environment="POLLIPI_CAMERA_LABEL=Module 3 NoIR Wide"
Environment=POLLIPI_CAMERA_MODEL=imx708_noir_wide
Environment=POLLIPI_CAMERA_PROFILE=module3_noir_wide_ir
Environment=POLLIPI_IS_AI_CAMERA=false
Environment=POLLIPI_IS_NOIR=true
Environment=POLLIPI_IS_WIDE=true
```

Important:

- NoIR does not magically see in complete darkness without illumination.
- For night trials, record IR illumination details in `notes`.
- Do not mix daylight RGB and IR/NoIR data without treating camera/illumination as a separate condition.

## 6. Configure systemd service

If `pollipi.service` is not installed yet, create it:

```bash
sudo nano /etc/systemd/system/pollipi.service
```

Recommended service (replace `pi` with your username):

```ini
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
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pollipi.service
sudo systemctl restart pollipi.service
sudo systemctl status pollipi.service --no-pager
```

## 7. Verify API and camera endpoints

Run:

```bash
curl http://localhost:8000/device
curl http://localhost:8000/status
curl -o /tmp/preview.jpg http://localhost:8000/preview
file /tmp/preview.jpg
```

Expected:

- `/device` shows correct `device_id`, `camera_label`, and `camera_profile`.
- `/status` returns JSON.
- `/preview` returns JPEG image data.

For Module 3 Wide `pollipi2.local` with device ID `pollipi2`, expected metadata includes:

```json
"device_id": "pollipi2",
"camera_label": "Module 3 Wide",
"camera_profile": "module3_wide_daylight",
"is_ai_camera": false,
"is_noir": false,
"is_wide": true
```

## 8. Check MJPEG and preview interaction

Because PolliPi uses both live monitor and still preview, verify they do not conflict.

```bash
timeout 3 curl "http://localhost:8000/mjpeg?detect=false" -o /tmp/mjpeg_test.bin
ls -lh /tmp/mjpeg_test.bin
curl -o /tmp/preview_after_mjpeg.jpg http://localhost:8000/preview
file /tmp/preview_after_mjpeg.jpg
```

Expected:

- MJPEG test file is created.
- `/preview_after_mjpeg.jpg` is still JPEG image data.

If `/preview_after_mjpeg.jpg` is ASCII text or says `Internal Server Error`, there is a camera lifecycle conflict between `/mjpeg` and `/preview`.

## 9. Check PWA from iPad

Open (replace `pollipi2.local` with your device hostname):

```text
http://pollipi2.local:8000/app/
```

Field usability test:

1. Tap `画角を確認`.
2. Confirm live monitor opens.
3. Adjust camera angle.
4. Tap `この画角でOK`.
5. Confirm still-frame ROI editor opens.
6. Draw or adjust ROI.
7. Tap `この花を使う`.
8. Confirm main screen shows ROI set.
9. Start recording.
10. Confirm `/status` updates.

## 10. Update project documents

When adding a new permanent device, update:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `FIELD_METHOD_ROADMAP.md` if needed
- `HANDOFF.md`
- `README.md` if the device list is shown there

At minimum, record:

- hostname
- camera type
- camera profile
- intended role
- setup date
- any special notes

## 11. Recommended handoff entry

Add a note like this to `HANDOFF.md`:

```md
## Handoff YYYY-MM-DD HH:MM JST

### Owner
Codex / Claude / ChatGPT / User

### Task
Added new PolliPi device `pollipi2.local`.

### What changed
- Configured as Module 3 Wide daylight unit.
- Set `DEVICE_ID=pollipi2`.
- Set `CAMERA_PROFILE=module3_wide_daylight`.

### Tests run
- `rpicam-hello --timeout 3000`
- `/device`
- `/status`
- `/preview`
- `/mjpeg` followed by `/preview`
- iPad PWA test

### Known issues
- item if any

### Next recommended task
One task only.
```

## 12. Troubleshooting

### `Camera __init__ sequence did not complete`

Check whether another process is using the camera:

```bash
ps aux | grep -E "python|picamera|libcamera|rpicam|mjpeg|pollipi|live_detect|訪花" | grep -v grep
```

Stop old standalone scripts if needed:

```bash
pkill -f mjpeg_server
pkill -f live_detect_mjpeg
pkill -f pollipi_api_server
pkill -f picamera
pkill -f rpicam
sudo systemctl restart pollipi.service
```

Then test:

```bash
curl -o /tmp/preview.jpg http://localhost:8000/preview
file /tmp/preview.jpg
```

### `/preview` works before MJPEG but fails after MJPEG

This indicates camera lifecycle conflict between `/mjpeg` and `/preview`.

Expected fix:

- shared camera manager
- camera lock
- cached latest MJPEG frame for `/preview`
- no repeated `Picamera2()` creation for preview/start while MJPEG is running

Do not treat this as a hardware failure until `rpicam-hello` also fails.
