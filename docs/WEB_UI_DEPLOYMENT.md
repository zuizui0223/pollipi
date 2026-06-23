# Web UI Auto-Deployment Guide

This guide explains how to quickly deploy web UI changes to your Raspberry Pi during development.

## Quick Deployment (One-time)

Deploy the current web UI build to the Pi:

```bash
./scripts/deploy_web_only.sh -h pollipi1.local -u pi
```

Or with environment variables:

```bash
PI_HOST=192.168.1.100 PI_USER=pi ./scripts/deploy_web_only.sh
```

**What it does:**
1. Checks if web UI is built (`pnpm build:web` if needed)
2. Verifies SSH connection to Pi
3. Syncs `packages/web/dist/` to `~/pollipi_timelapse/web/dist/` on Pi
4. Done — iPad will see changes on next refresh

## Continuous Auto-Sync (Development Mode)

For iterative development, watch for changes and auto-sync:

```bash
./scripts/watch_web_and_sync.sh -h pollipi1.local -u pi
```

Or with environment variables:

```bash
PI_HOST=192.168.1.100 PI_USER=pi ./scripts/watch_web_and_sync.sh
```

**What it does:**
1. Watches `packages/web/src/` for changes
2. On any change:
   - Rebuilds: `pnpm build:web`
   - Syncs: `rsync` to Pi
   - Notifies completion
3. iPad updates on next refresh (Cmd+Shift+R to force)

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
./scripts/deploy_web_only.sh -h pollipi1.local -u pi
```

### Development Loop

Terminal 1 — Start auto-sync:
```bash
./scripts/watch_web_and_sync.sh -h pollipi1.local -u pi
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

iPad:
```
1. Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Linux/Windows)
2. See changes immediately
```

## Troubleshooting

### Connection Fails
```bash
# Check SSH access
ssh pi@pollipi1.local "echo 'Connected!'"

# Test with IP instead
./scripts/deploy_web_only.sh -h 192.168.1.100 -u pi

# Custom SSH port
./scripts/deploy_web_only.sh -h pollipi1.local -u pi -p 2222
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
1. Hard refresh browser: **Cmd+Shift+R** (Mac) or **Ctrl+Shift+R** (Linux)
2. Close browser entirely and reopen
3. Check rsync succeeded: `./scripts/deploy_web_only.sh` should show "✓ Deployment complete!"

### File Permissions
If deployment fails with permission error:
```bash
ssh pi@pollipi1.local
mkdir -p ~/pollipi_timelapse/web/dist/
chmod 755 ~/pollipi_timelapse/web/
```

## Integration with Full Deployment

For server code changes, use the full deployment:

```bash
# Web UI + Server code
./scripts/deploy_pi.sh -h pollipi1.local -u pi
```

## Environment Variables

Set these to avoid typing flags repeatedly:

```bash
# ~/.bashrc or ~/.zshrc
export PI_HOST="pollipi1.local"
export PI_USER="pi"
export PI_PORT="22"

# Now just run
./scripts/deploy_web_only.sh
./scripts/watch_web_and_sync.sh
```
