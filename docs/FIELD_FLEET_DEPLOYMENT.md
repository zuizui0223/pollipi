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

Live execution requires both flags after reviewing the printed plan:

```powershell
python tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --execute --confirm-live-deploy
```

For each Pi the plan is:

1. Preflight: confirm local artifacts exist.
2. Preflight: confirm the PC is on the configured GL LAN subnet.
3. Preflight: confirm SSH and HTTP reachability.
4. Preflight: check `/device` and `/status`.
5. Prepare the remote install and web directories.
6. Back up the current server artifact with a timestamp.
7. Back up the current web build with a timestamp.
8. Upload `dist/pollipi_api_server.py`.
9. Upload the built web assets.
10. Restart the configured systemd service.
11. Confirm `/device` reports the expected `deployment_mode`, `git_commit`, and `web_build_id`.

Rollback policy:

- If upload, restart, or version verification fails, the tool restores the timestamped backups and restarts the configured service.
- If rollback itself fails, restore the server artifact backup and web backup manually over SSH, then restart the configured service.
- Re-check `/device` and `/status` from the iPad before field use.

The deployment tool does not require WAN, cloud APIs, Git on the Pi, or a coordinator. It only uses SSH/SCP inside the local LAN plus direct HTTP checks against each Pi.
