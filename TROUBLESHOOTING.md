# PolliPi Troubleshooting

> **Note:** The single-file `install.sh` / `setup_device.sh` deployment is removed;
> the service now runs the packaged `dist/pollipi_api_server.py` deployed via
> `tools/pollipi_fleet_deploy.py`. Command references below that mention the old
> single-file path are historical.

## Camera issues

### `Camera __init__ sequence did not complete`

Another process is using the camera. Check:

```bash
ps aux | grep -E "python|picamera|libcamera|rpicam|mjpeg|pollipi" | grep -v grep
```

Stop conflicting processes and restart:

```bash
pkill -f mjpeg_server
pkill -f pollipi_api_server
pkill -f picamera
pkill -f rpicam
sudo systemctl restart pollipi.service
```

Then verify:

```bash
curl -o /tmp/preview.jpg http://localhost:8000/preview
file /tmp/preview.jpg
```

### `rpicam-hello` shows no cameras

- Check cable — Camera Module 3 uses a 15-pin ribbon cable (not the older 22-pin connector on Pi 4)
- Run `sudo raspi-config` → Interface Options → Legacy Camera (should be disabled on Bookworm)
- Reboot after cable changes
- For AI Camera: run `sudo apt install -y imx500-all && sudo reboot` before testing

### `/preview` works before MJPEG but fails after MJPEG

Camera lifecycle conflict between `/mjpeg` and `/preview`. Do not treat as hardware failure until `rpicam-hello` also fails. This is a software-side resource conflict — restart the service:

```bash
sudo systemctl restart pollipi.service
```

---

## Service / systemd issues

### Service fails to start

Check logs:

```bash
sudo systemctl status pollipi.service --no-pager
sudo journalctl -u pollipi.service -n 50 --no-pager
```

Common causes:
- Python path wrong: verify `.venv` exists in `WorkingDirectory`
- Wrong `User=` in service file (should match the user who ran `install.sh`)
- Missing `camera-profile.conf` drop-in — run `setup_device.sh` again
- Camera not detected at boot — add `After=network-online.target` and ensure camera cable is seated

### Service starts but API returns errors

```bash
curl http://localhost:8000/device
curl http://localhost:8000/status
```

If you get connection refused, the service is not running. If you get 500 errors, check journalctl for Python tracebacks.

### Device profile not applied

Check the drop-in file exists:

```bash
cat /etc/systemd/system/pollipi.service.d/camera-profile.conf
sudo systemctl daemon-reload
sudo systemctl restart pollipi.service
curl http://localhost:8000/device
```

---

## Network / PWA issues

### Cannot reach `pollipi1.local` from iPad

- iPad and Pi must be on the same Wi-Fi network
- `.local` mDNS resolution requires Bonjour/Avahi — works natively on iOS/macOS, may need Bonjour Print Services on Windows
- Try the Pi's IP address instead: `http://192.168.x.x:8000/app/`
- On Pi: `hostname -I` shows current IPs

### PWA shows "Failed to fetch" for a device

- The Pi for that device is unreachable (off, wrong network, service stopped)
- Check `sudo systemctl status pollipi.service` on that Pi
- Verify the address entered in the PWA is correct — enter `pi@pollipi1` or `pollipi1.local:8000`

### PWA does not update after code change

- Hard-refresh in Safari: hold reload button → Reload Without Content Blockers, or Settings → Safari → Clear History and Website Data
- Service worker cache may be stale — open `http://pollipi1.local:8000/app/` and force reload

---

## Deployment issues (Windows)

### `deploy_pollipi_pi.ps1` fails with SSH error

- Set the password: `$env:POLLIPI_DEPLOY_PASSWORD = "your_password"`
- Or configure SSH keys and remove `-o PreferredAuthentications=password` from the script
- Check that `ssh your_user@your_hostname.local` works from PowerShell first

### SCP times out or fails

- Confirm Pi is reachable: `ping pollipi1.local`
- Use IP address for `-HostName` if `.local` is not resolving: `.\deploy_pollipi_pi.ps1 -HostName 192.168.x.x -DeviceId pollipi1 -Preset module3-wide`

---

## Storage / image issues

### Disk full on Pi

Check usage:

```bash
df -h ~
df -h /media  # if using USB storage
```

Delete old images from the PWA (Trash icon), or via API:

```bash
curl -X DELETE http://localhost:8000/images \
  -H "Content-Type: application/json" \
  -d '{"confirm": "DELETE_ALL"}'
```

To use external USB storage, set `POLLIPI_IMAGE_DIR` in the camera-profile drop-in:

```ini
Environment="POLLIPI_IMAGE_DIR=/media/your_user/POLLIPI/images"
```

### Images saved but not visible in PWA

The PWA fetches `/images?limit=40` — newest first. If images exist but don't appear, check:

```bash
curl "http://localhost:8000/images?limit=10"
ls ~/pollipi_timelapse/images/ | head -10
```

---

## Autonomous mode issues

### Recording stopped after reboot and did not resume

Autonomous mode requires `autonomous_mode: true` in the start request. The resume state is saved in `~/pollipi_timelapse/autonomous_run.json`. If this file is missing, autonomous resume will not trigger. Check:

```bash
cat ~/pollipi_timelapse/autonomous_run.json
```

If missing, start again from the PWA with Autonomous mode enabled.

### Recording resumes but with wrong interval

The interval is saved in `autonomous_run.json`. Edit the file or stop and restart from the PWA.
