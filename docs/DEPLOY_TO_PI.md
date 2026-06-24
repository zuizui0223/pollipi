# PolliPi deployment guide

This is the current deployment guide for the packaged PolliPi server and iPad web app. It replaces the legacy one-Pi source-sync instructions.

## Source of truth

- Server source: `packages/server`
- Web source: `packages/web`
- Deployable server artifact: `dist/pollipi_api_server.py`
- Fleet deployment authority: `tools/pollipi_fleet_deploy.py`

Do not use legacy `deploy_pi.sh`, `deploy_pi.ps1`, Pi-side `git pull`, or source-directory rsync for the active five-Pi fleet.

## Before deployment

You need:

- a development machine on the same private LAN as the target Pis;
- SSH key access to every Pi;
- the configured service restart permission for the deployment user;
- a fleet configuration that names the real SSH user, IPs/hostnames, remote install directory, service name, and web path;
- Python and pnpm installed on the development machine.

For the current fleet, the deployment user is `zuizui0223`. Use router DHCP reservations or explicit local-LAN IPs rather than depending on mDNS during a field deployment.

## Build artifacts

Run from the repository root on Windows, macOS, Linux, or WSL:

```bash
pnpm install
pnpm check:web
pnpm build:artifacts
```

`build:artifacts` builds the web app first and then creates `dist/pollipi_api_server.py`, ensuring the packaged server contains the matching web build ID.

For a web-only change, run:

```bash
pnpm check:web
pnpm build:web
```

Do not rebuild or replace the server artifact for a web-only deployment.

## Fleet configuration

Copy the example configuration and keep the local file out of version control:

```text
tools/fleet.example.json -> tools/fleet.local.json
```

The configuration must define:

- local LAN subnet;
- `ssh_user`;
- each Pi host/IP;
- `remote_dir`;
- `service_name`;
- `server_artifact` and `web_build_dir`;
- `post_deploy_base_url`.

For field work, use the router's DHCP reservations as the host/IP values. Do not rewrite Pi network configuration for each site.

## Dry-run first

```powershell
python tools\pollipi_fleet_deploy.py --config tools\fleet.local.json
```

Review all of the following before live execution:

- expected server commit and web build ID;
- only the intended Pi addresses;
- `BatchMode=yes` and `ConnectTimeout=8` on remote commands;
- root API checks at `/device` and `/status`;
- backup, upload, restart, and post-deployment verification steps.

## Full server + web deployment

```powershell
python tools\pollipi_fleet_deploy.py `
  --config tools\fleet.local.json `
  --execute `
  --confirm-live-deploy
```

For each Pi, the tool:

1. verifies local artifacts and subnet;
2. verifies non-interactive SSH authentication and allowed service access;
3. checks `/device` and `/status` before changing files;
4. backs up the installed server artifact and web directory;
5. uploads the new artifact and web files;
6. restarts the configured service;
7. verifies that `/device` reports the expected packaged artifact commit and web build ID.

The tool stops at the first failed Pi. If an upload, restart, or post-deploy verification step fails, it restores timestamped backups for that Pi and attempts to restart the service again.

## Web-only deployment

Use this only when the server artifact is intentionally unchanged:

```powershell
python tools\pollipi_fleet_deploy.py `
  --config tools\fleet.local.json `
  --web-only `
  --execute `
  --confirm-live-deploy
```

Do not use `--web-only`, `--apply`, or `--latest-main-web-only` for a release that changes server behavior, policy profiles, API schemas, capture logic, or packaging.

## Post-deployment checks

For every Pi:

```text
GET /device
GET /status
GET /policy-profiles
GET /app/
GET /app/build-info.json
```

Confirm:

- `deployment_mode=packaged_artifact`;
- expected `git_commit` and `web_build_id`;
- `live_adaptive_enabled=false`;
- expected policy profiles are available;
- iPad PWA loads the current build.

The iPad may keep an old PWA JavaScript bundle. When a new screen does not appear, close and reopen Safari or use a cache-busting URL such as:

```text
http://<pi-ip>:8000/app/?build=<short-commit>
```

## Do not deploy during a capture session

A full deployment restarts `pollipi.service`. Confirm all target Pis are stopped before deploying. After deployment, run a short fixed-interval capture test before leaving the system unattended.

## Field-router deployment

Deployment requires only the local router LAN. WAN, cloud services, GitHub access from the Pi, and a coordinator are not required once the development machine has already built the artifacts.

See [FIELD_FLEET_DEPLOYMENT.md](FIELD_FLEET_DEPLOYMENT.md) and [FIELD_READINESS_CHECKLIST.md](FIELD_READINESS_CHECKLIST.md) for field-specific checks.
