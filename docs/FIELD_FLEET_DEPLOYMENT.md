# PolliPi field fleet updates

This workflow is for a WAN-free GL.iNet local LAN where the iPad and Pi devices are on `192.168.8.0/24`.

The tool is dry-run by default and does not assume the SSH user, systemd service name, or Pi install path. Copy `tools/fleet.example.json`, replace every `CHANGE_ME`, and keep the five GL LAN IPs:

- `192.168.8.11`
- `192.168.8.12`
- `192.168.8.13`
- `192.168.8.14`
- `192.168.8.15`

Dry-run:

```powershell
python tools/pollipi_fleet_deploy.py --config tools/fleet.local.json
```

Execute after reviewing the printed plan:

```powershell
python tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --execute
```

For each Pi the plan is:

1. Prepare the remote install and web directories.
2. Back up the current server artifact with a timestamp.
3. Back up the current web build with a timestamp.
4. Upload `dist/pollipi_api_server.py`.
5. Upload the built web assets.
6. Restart the configured systemd service.
7. Check `/device`.
8. Check `/status`.

Rollback policy:

- If upload or restart fails, keep the timestamped backups.
- Restore the server artifact backup and web backup manually over SSH, then restart the configured service.
- Re-check `/device` and `/status` from the iPad before field use.

The deployment tool does not require WAN, cloud APIs, Git on the Pi, or a coordinator. It only uses SSH/SCP inside the local LAN plus direct HTTP checks against each Pi.
