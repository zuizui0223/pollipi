# PolliPi Device Onboarding Guide

This document describes how to add a new Raspberry Pi camera unit to the PolliPi field observer system.

Use this when adding a new hostname such as `zuizui5.local`, `zuizui6.local`, etc.

## 1. Decide the device role

Before setup, decide the hostname and camera type.

Current known roles:

| Hostname | Camera | Role |
|---|---|---|
| `zuizui.local` | Camera Module 3 Wide | standard daylight unit |
| `zuizui2.local` | Raspberry Pi AI Camera | AI Camera comparison / detection-test unit |
| `zuizui3.local` | Camera Module 3 NoIR Wide | NoIR / low-light / IR-capable unit |
| `zuizui4.local` | Camera Module 3 / Module 3 Wide | standard daylight unit |
| `zuizui5.local` | Camera Module 3 Wide | standard daylight unit |

Default rule:

- AI Camera: set `IS_AI_CAMERA=true`.
- NoIR Wide: set `IS_NOIR=true`.
- Module 3 Wide: set `IS_WIDE=true` and use `module3_wide_daylight` profile.

## 2. Confirm SSH access

From Windows PowerShell:

```powershell
ssh zuizui0223@zuizui5.local
```

Replace `zuizui5.local` with the new hostname.

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

### If this is a fresh Pi

```bash
cd /home/zuizui0223
git clone https://github.com/zuizui0223/raspberry-pi-camera-project.git pollipi_timelapse
cd pollipi_timelapse
```

### If the repository already exists

```bash
cd /home/zuizui0223/pollipi_timelapse
git pull origin main
```

### Windows deployment helper

From the Windows workspace, the deployment helper can copy source files, set the camera profile, run syntax checks, install the service, and restart PolliPi.

Standard daylight Module 3 Wide example for `zuizui5.local`:

```powershell
$env:POLLIPI_DEPLOY_PASSWORD = "your_pi_password"
.\deploy_pollipi_pi.ps1 -HostName zuizui5.local -Preset module3-wide -DeviceId zuizui5 -InstallDependencies
```

After the first deployment, `-InstallDependencies` can usually be omitted:

```powershell
$env:POLLIPI_DEPLOY_PASSWORD = "your_pi_password"
.\deploy_pollipi_pi.ps1 -HostName zuizui5.local -Preset module3-wide -DeviceId zuizui5
```

If `.local` name resolution is not working but the IP address is known, use the IP address for `-HostName` and keep `-DeviceId` as the intended stable device id:

```powershell
.\deploy_pollipi_pi.ps1 -HostName 192.168.11.25 -Preset module3-wide -DeviceId zuizui5
```

## 5. Configure device profile

Create or edit the systemd drop-in file:

```bash
sudo mkdir -p /etc/systemd/system/pollipi.service.d
sudo nano /etc/systemd/system/pollipi.service.d/camera-profile.conf
```

### Module 3 Wide example: `zuizui5.local`

```ini
[Service]
Environment=POLLIPI_DEVICE_ID=zuizui5
Environment="POLLIPI_DEVICE_NAME=Site Module 3 Wide 5"
Environment="POLLIPI_CAMERA_LABEL=Module 3 Wide"
Environment=POLLIPI_CAMERA_MODEL=imx708_wide
Environment=POLLIPI_CAMERA_PROFILE=module3_wide_daylight
Environment=POLLIPI_IS_AI_CAMERA=false
Environment=POLLIPI_IS_NOIR=false
Environment=POLLIPI_IS_WIDE=true
```

### AI Camera example: `zuizui2.local`

```ini
[Service]
Environment=POLLIPI_DEVICE_ID=zuizui2
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

### NoIR Wide example: `zuizui3.local`

```ini
[Service]
Environment=POLLIPI_DEVICE_ID=zuizui3
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

Recommended service:

```ini
[Unit]
Description=PolliPi Field Observer API
After=network-online.target
Wants=network-online.target

[Service]
User=zuizui0223
WorkingDirectory=/home/zuizui0223/pollipi_timelapse
ExecStart=/usr/bin/python3 -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 3
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

For Module 3 Wide `zuizui5.local`, expected metadata includes:

```json
"device_id": "zuizui5",
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

Open:

```text
http://zuizui5.local:8000/app/
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
Added new PolliPi device `zuizui5.local`.

### What changed
- Configured as Module 3 Wide daylight unit.
- Set `DEVICE_ID=zuizui5`.
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
