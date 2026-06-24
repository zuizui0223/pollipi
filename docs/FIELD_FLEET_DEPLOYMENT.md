# PolliPi field fleet deployment

This workflow is for a **WAN-free private field LAN**. The router is only a Wi-Fi access point and DHCP server for the development machine, iPad, and Raspberry Pi units. It does not need an internet uplink, cloud account, coordinator, or Git installation on the Pis.

## Before you travel

1. Configure the field router with a fixed SSID and password.
2. Enable DHCP and disable guest/AP/client isolation.
3. Reserve one address per Pi on the router.
4. Record the reservations in the field notebook and in `tools/fleet.local.json`.

A typical field subnet is `192.168.8.0/24` with five Pi reservations:

```text
192.168.8.11
192.168.8.12
192.168.8.13
192.168.8.14
192.168.8.15
```

These are examples, not required addresses. Use the router's actual reservations.

## Build once on the development machine

```powershell
pnpm install
pnpm check:web
pnpm build:artifacts
```

Build before leaving the office or before connecting to the WAN-free field router. The Pis do not build or fetch packages during deployment.

## Configure the fleet

Copy the example configuration:

```text
tools/fleet.example.json -> tools/fleet.local.json
```

Set the real field subnet, `ssh_user`, Pi IPs, remote directory, service name, server artifact path, web build directory, and post-deploy app URL. Keep this local configuration out of version control.

## Dry-run

```powershell
python tools\pollipi_fleet_deploy.py --config tools\fleet.local.json
```

Review that the output includes only the intended field Pi IPs, root API checks (`/device`, `/status`), non-interactive SSH commands, backups, server/web uploads, restart, and version verification.

## Live full deployment

```powershell
python tools\pollipi_fleet_deploy.py `
  --config tools\fleet.local.json `
  --execute `
  --confirm-live-deploy
```

For each Pi the tool:

1. verifies local artifacts;
2. verifies that the development machine is on the expected field subnet;
3. verifies SSH, sudo/service access, and HTTP reachability;
4. backs up the current server artifact and web directory;
5. uploads `dist/pollipi_api_server.py` and `packages/web/dist/`;
6. restarts `pollipi.service`;
7. confirms `/device` reports the expected packaged artifact commit and web build ID.

If upload, restart, or version verification fails, the tool restores timestamped backups for that Pi and attempts to restart its service. It stops at the first failed Pi.

## After deployment

1. On the iPad, open `http://<console-pi-ip>:8000/app/`.
2. Add each Pi by its reserved IP address.
3. Confirm all cards show the expected build.
4. Run a short fixed-interval capture test before field placement.
5. Complete the router-disconnect and Pi-reboot checks in [FIELD_READINESS_CHECKLIST.md](FIELD_READINESS_CHECKLIST.md).

## Web-only changes

A web-only deployment is appropriate only when the server artifact is intentionally unchanged. Use the explicit `--web-only` mode after a dry-run. Do not use it for policy/API/capture/runtime changes.
