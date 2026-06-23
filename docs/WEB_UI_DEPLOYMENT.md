# Web UI Deployment Guide

This guide explains how to deploy web UI changes to your Raspberry Pi during development.

## Fleet Deployment (Recommended)

Deploy the web UI to all five Pis in sequence with automatic verification and rollback:

```bash
python3 tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --web-only --execute --confirm-live-deploy
```

Dry-run first (no changes made):

```bash
python3 tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --web-only
```

## Quick Deployment (Single Pi)

Deploy the current web UI build to one Pi:

```bash
./scripts/deploy_web_only.sh -h zuizui.local -u zuizui0223
```

Both `-h` (host) and `-u` (user) are **required**. There are no defaults.

**What it does:**
1. Checks if web UI is built (`pnpm build:web` if needed)
2. Verifies SSH connection to Pi
3. Syncs `packages/web/dist/` to `/home/<user>/pollipi_timelapse/web/` on Pi
4. Done — iPad will see changes on next page load

## Continuous Auto-Sync (Development Mode)

For iterative development, watch for changes and auto-sync to one Pi:

```bash
./scripts/watch_web_and_sync_one_pi.sh -h zuizui.local -u zuizui0223
```

Both `-h` (host) and `-u` (user) are **required**. There are no defaults.

**What it does:**
1. Watches `packages/web/src/` for changes
2. On any change:
   - Rebuilds: `pnpm build:web`
   - Syncs: `rsync` to Pi
   - Notifies completion
3. iPad will see changes on next page load

**Requirements:**
- `fswatch` for file monitoring (optional, falls back to polling)
  - macOS: `brew install fswatch`
  - Linux: `apt install fswatch`
- SSH access to Pi
- `rsync` installed

## Workflow Example

### Initial Setup

```bash
# Build web UI
pnpm build:web

# First deploy
./scripts/deploy_web_only.sh -h zuizui.local -u zuizui0223
```

### Development Loop

Terminal 1 — Start auto-sync:
```bash
./scripts/watch_web_and_sync_one_pi.sh -h zuizui.local -u zuizui0223
```

Terminal 2 — Edit and see changes:
```bash
# Edit packages/web/src/components/DeviceCard.tsx
# Auto-sync will:
# 1. Detect change
# 2. Build
# 3. Sync to Pi
# 4. Print completion message
```

iPad (Safari):
```
1. Tap the reload button, or close Safari completely and reopen the URL.
2. For cache-busting, append a query string: http://zuizui.local:8000/app/?v=1
3. See changes immediately.
```

## Troubleshooting

### Connection Fails
```bash
# Check SSH access
ssh zuizui0223@zuizui.local "echo 'Connected!'"

# Test with IP instead
./scripts/deploy_web_only.sh -h 192.168.11.10 -u zuizui0223

# Custom SSH port
./scripts/deploy_web_only.sh -h zuizui.local -u zuizui0223 -p 2222
```

### Build Fails
```bash
# Check for TypeScript errors
pnpm check:web

# Manual rebuild
pnpm build:web

# View build log
less /tmp/web_build.log
```

### Changes Don't Appear on iPad
1. In Safari on iPad: tap and hold the reload button, then select "Reload Without Content Blockers" or simply close Safari entirely and reopen the URL.
2. Alternatively, append a cache-busting query string: `http://zuizui.local:8000/app/?v=$(date +%s)`
3. Check rsync succeeded: `./scripts/deploy_web_only.sh` should show "✓ Deployment complete!"

### File Permissions
If deployment fails with permission error:
```bash
ssh zuizui0223@zuizui.local
mkdir -p ~/pollipi_timelapse/web/
chmod 755 ~/pollipi_timelapse/web/
```

## Integration with Full Deployment

For server code changes, use the full fleet deployment:

```bash
python3 tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --execute --confirm-live-deploy
```
