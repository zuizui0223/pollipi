# PolliPi Device Onboarding Guide

This document describes how to add a new Raspberry Pi camera unit to the
PolliPi field observer system, using the packaged artifact +
`tools/pollipi.service.template` and `tools/pollipi_fleet_deploy.py` per
[docs/DEPLOY_TO_PI.md](docs/DEPLOY_TO_PI.md) and
[docs/FIELD_FLEET_DEPLOYMENT.md](docs/FIELD_FLEET_DEPLOYMENT.md).

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

### Current fleet (`tools/fleet.zuizui.json`)

- `zuizui.local`, `zuizui4.local`, `zuizui5.local` — Camera Module 3 / Module 3
  Wide, ordinary standard daylight units.
- `zuizui2.local` — Raspberry Pi AI Camera (IMX500). Comparison / on-device
  detection-test unit; the default IMX500 model is not an insect classifier,
  so do not treat its output as species identification without a validated
  dedicated model.
- `zuizui3.local` — Camera Module 3 NoIR Wide, low-light/night-capable unit.
  NoIR does not see in complete darkness without IR illumination; treat
  NoIR/IR captures as a distinct condition from daylight RGB.

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

## 4. Build and deploy the packaged artifact

On the development machine, build once:

```bash
pnpm install
pnpm check:web
pnpm build:artifacts
```

Add the new Pi to your fleet configuration (copy `tools/fleet.example.json` to
`tools/fleet.local.json` if you have not already), then dry-run and deploy:

```bash
python tools/pollipi_fleet_deploy.py --config tools/fleet.local.json
python tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --execute --confirm-live-deploy
```

This uploads `dist/pollipi_api_server.py` and the web build, installs the
service from `tools/pollipi.service.template`, and starts it. See
[docs/DEPLOY_TO_PI.md](docs/DEPLOY_TO_PI.md) for the full deployment
reference.

## 5. Configure device profile

Set the camera-specific environment variables as a systemd drop-in on the Pi.
Create or edit:

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

The fleet deploy in step 4 installs `pollipi.service` from
`tools/pollipi.service.template` automatically. If you need to (re)install it
by hand on the Pi:

```bash
sudo cp tools/pollipi.service.template /etc/systemd/system/pollipi.service
sudo sed -i "s|DEVICE_ID|pollipi2|; s|POLLIPI_HOME|/home/pi/pollipi_timelapse|g; s|CONFIG_FILE|/home/pi/pollipi_timelapse/config.env|" /etc/systemd/system/pollipi.service
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

1. Confirm the device card appears and shows `online`.
2. Choose **① Plain timelapse** and set the baseline interval (normally 30 sec).
3. Enable **Resume autonomously after Pi restart** if reboot recovery is required.
4. Tap **Start**.
5. Confirm the card shows `capturing`, the intended `High-res interval`, and advancing `Last saved` / `Saved photos` at least twice.

## 10. Update project documents

When adding a new permanent device, update the "Current fleet" table in
section 1 of this document, and `README.md` if the device list is shown
there.

At minimum, record:

- hostname
- camera type
- camera profile
- intended role
- setup date
- any special notes

## 11. Troubleshooting

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
