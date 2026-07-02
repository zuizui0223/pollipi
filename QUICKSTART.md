# PolliPi Quickstart

This guide gets one Raspberry Pi running PolliPi from scratch. It builds the
packaged deployable artifact on your development machine and deploys it with
`tools/pollipi_fleet_deploy.py`, per [docs/DEPLOY_TO_PI.md](docs/DEPLOY_TO_PI.md).
For adding more devices to an existing fleet, see `DEVICE_ONBOARDING.md`.
For troubleshooting, see `TROUBLESHOOTING.md`.

## What you need

- Raspberry Pi 5 (or Pi 4)
- Raspberry Pi Camera Module 3 (Wide or standard), Camera Module 3 NoIR Wide, or Raspberry Pi AI Camera
- Raspberry Pi OS Bookworm (64-bit recommended)
- A development machine with Python and `pnpm` for building and deploying the artifact
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

## Step 2 — Build the artifacts on the development machine

```bash
pnpm install
pnpm check:web
pnpm build:artifacts
```

This produces `dist/pollipi_api_server.py` (server, with the matching embedded
web build) and `packages/web/dist/` (web build).

## Step 3 — Configure and deploy with the fleet tool

Copy `tools/fleet.example.json` to `tools/fleet.local.json`, set the Pi's
host/IP, SSH user, and remote directory, then dry-run and deploy:

```bash
python tools/pollipi_fleet_deploy.py --config tools/fleet.local.json
python tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --execute --confirm-live-deploy
```

This uploads the artifact and web build, installs the systemd service from
`tools/pollipi.service.template`, and restarts it. See
[DEVICE_ONBOARDING.md](DEVICE_ONBOARDING.md) for the camera-profile
environment variables for your specific camera.

## Step 4 — Verify

```bash
curl http://localhost:8000/device
curl http://localhost:8000/status
curl -o /tmp/preview.jpg http://localhost:8000/preview && file /tmp/preview.jpg
```

Expected: `/device` returns JSON with your device_id and camera_profile; `/preview` is a JPEG image.

## Step 5 — Open the PWA

On your iPad or browser, connect to the same Wi-Fi as the Pi, then open:

```
http://pollipi1.local:8000/app/
```

In Safari on iPad, use **Share → Add to Home Screen** to install it as an app icon.

## Field workflow

1. Confirm the device card is online and aim the camera at your target.
2. Choose **① Plain timelapse** and set the baseline interval (normally 30 sec) for routine field work.
3. Enable **Resume autonomously after Pi restart** if reboot recovery is required.
4. Tap **Start**. The Pi records independently after this — closing the PWA or losing Wi-Fi does not stop capture.
5. Confirm `capturing`, the intended `High-res interval`, and advancing `Last saved` / `Saved photos` at least twice before leaving the system unattended.

See [README.md](README.md) for the full description of capture modes ①②③④ and when to use each.

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
