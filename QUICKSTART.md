# PolliPi Quickstart

> **Note:** The single-file `install.sh` / `setup_device.sh` flow has been removed.
> Deploy the packaged artifact via [docs/DEPLOY_TO_PI.md](docs/DEPLOY_TO_PI.md) and
> `tools/pollipi_fleet_deploy.py`. The camera-setup steps below remain useful.

This guide gets one Raspberry Pi running PolliPi from scratch in about 15 minutes.
For adding more devices to an existing fleet, see `DEVICE_ONBOARDING.md`.
For troubleshooting, see `TROUBLESHOOTING.md`.

## What you need

- Raspberry Pi 5 (or Pi 4)
- Raspberry Pi Camera Module 3 (Wide or standard), Camera Module 3 NoIR Wide, or Raspberry Pi AI Camera
- Raspberry Pi OS Bookworm (64-bit recommended)
- iPad or any browser on the same Wi-Fi

## Step 1 — Confirm the camera works

On the Pi:

```bash
rpicam-hello --list-cameras
rpicam-hello --timeout 3000
```

If no camera is listed, check the cable connection and enable the camera interface. Do not proceed until `rpicam-hello` succeeds.

For AI Camera only — install firmware first:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y imx500-all
sudo reboot
```

## Step 2 — Copy files to the Pi

From your PC (replace `pi` with your Pi username and `pollipi1.local` with your Pi's hostname):

```bash
scp pollipi_api_server.py install.sh setup_device.sh pi@pollipi1.local:~/
scp -r web pi@pollipi1.local:~/pollipi_timelapse/web 2>/dev/null || true
```

Or clone directly on the Pi:

```bash
git clone https://github.com/YOUR_FORK/pollipi.git ~/pollipi_timelapse
```

## Step 3 — Install on the Pi

SSH into the Pi:

```bash
ssh pi@pollipi1.local
```

Move files to the install directory and run:

```bash
mkdir -p ~/pollipi_timelapse
mv ~/pollipi_api_server.py ~/install.sh ~/setup_device.sh ~/pollipi_timelapse/
cd ~/pollipi_timelapse
bash install.sh
```

## Step 4 — Configure device profile

```bash
bash ~/pollipi_timelapse/setup_device.sh pollipi1
```

`setup_device.sh` will ask you to:
1. Choose your camera type (Module 3 Wide / NoIR Wide / AI Camera)
2. Enter a display name for the device (shown in the PWA)

It then writes the systemd service and camera-profile drop-in, and starts the service.

## Step 5 — Verify

```bash
curl http://localhost:8000/device
curl http://localhost:8000/status
curl -o /tmp/preview.jpg http://localhost:8000/preview && file /tmp/preview.jpg
```

Expected: `/device` returns JSON with your device_id and camera_profile; `/preview` is a JPEG image.

## Step 6 — Open the PWA

On your iPad or browser, connect to the same Wi-Fi as the Pi, then open:

```
http://pollipi1.local:8000/app/
```

In Safari on iPad, use **Share → Add to Home Screen** to install it as an app icon.

## Field workflow

1. **画角確認** — tap `画角を確認` in the PWA to open the live monitor. Aim the camera at your flower/target.
2. **ROI指定** — tap `この画角でOK`, then draw a rectangle around the flower on the still frame. Tap `このROIで決定`.
3. **撮影開始** — set interval, enable Autonomous mode, tap Start. The Pi records independently after this.
4. **レビュー** — reconnect later, open EVENT REVIEW to check motion candidates. Correct labels as needed.

## Hotspot mode (offline field use)

To use the Pi as its own Wi-Fi access point:

```bash
sudo nmcli device wifi hotspot ssid PolliPi-site01 password 'change-this-password'
```

Connect your iPad to `PolliPi-site01`, then open `http://192.168.x.x:8000/app/` (check Pi's IP with `hostname -I`).

## Multiple devices

Add more Pi units by following `DEVICE_ONBOARDING.md`. Each device needs a unique hostname, device ID, and camera profile. The PWA supports any number of devices — register each by entering its address in the **Raspberry Pi を追加** field.

## Next steps

- `DEVICE_ONBOARDING.md` — checklist for adding more Pi units
- `TROUBLESHOOTING.md` — common errors and fixes
- `README.md` — full documentation including API reference and research workflow
