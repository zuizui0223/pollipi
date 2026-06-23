# PolliPi Deployment Guide

This guide describes how to deploy PolliPi to a Raspberry Pi using the production-ready deployment scripts.

## Prerequisites

Before you start, ensure:

1. **Raspberry Pi OS Bookworm** (64-bit recommended) is installed and updated
2. **Camera interface enabled** and camera working (test with `rpicam-hello`)
3. **SSH access configured** (public key or password authentication)
4. **Network connectivity** on both development machine and Pi
5. **Python 3.11+** on the Pi

For camera setup, see [QUICKSTART.md](../QUICKSTART.md) — Step 1.

## Quick Start

### For macOS / Linux / WSL Users

1. **Build artifacts** (on your development machine):

   ```bash
   pnpm build:server
   pnpm build:web
   ```

2. **Deploy to Pi** (using the deploy script):

   ```bash
   ./scripts/deploy_pi.sh -h pollipi1.local -u pi
   ```

   The script will:
   - Verify SSH connectivity
   - Build fresh artifacts
   - Sync source code and builds to the Pi
   - Install Python dependencies
   - Enable and restart the systemd service
   - Perform a health check

### For Windows Users (PowerShell)

1. **Build artifacts** (in PowerShell):

   ```powershell
   pnpm build:server
   pnpm build:web
   ```

2. **Deploy to Pi** (using the deployment script):

   ```powershell
   .\scripts\deploy_pi.ps1 -HostName pollipi1.local -UserName pi
   ```

   The script will perform the same steps as the Unix version.

## Deployment Options

### Environment Variables (Linux/macOS/WSL)

Set these before running `deploy_pi.sh`:

```bash
PI_HOST=pollipi1.local     # Hostname or IP address (default: pollipi1.local)
PI_USER=pi                  # SSH username (default: pi)
PI_PORT=22                  # SSH port (default: 22)
DEVICE_ID=pollipi1          # Device identifier (default: hostname without .local)
```

Example:

```bash
export PI_HOST=192.168.1.100
export PI_USER=pi
export PI_PORT=2222
./scripts/deploy_pi.sh
```

### Command-line Arguments (Linux/macOS/WSL)

```bash
./scripts/deploy_pi.sh -h pollipi1.local -u pi -p 22 -d pollipi1
```

Arguments:
- `-h` — Hostname or IP address
- `-u` — SSH username
- `-p` — SSH port
- `-d` — Device identifier

### PowerShell Parameters (Windows)

```powershell
.\scripts\deploy_pi.ps1 -HostName pollipi1.local -UserName pi -Port 22 -DeviceId pollipi1
```

Parameters:
- `-HostName` — Hostname or IP address
- `-UserName` — SSH username
- `-Port` — SSH port (default: 22)
- `-DeviceId` — Device identifier

## Deployment Steps (Manual)

If you prefer to deploy manually, or for troubleshooting:

### 1. Build artifacts on development machine

```bash
pnpm build:server  # Creates dist/pollipi_api_server.py
pnpm build:web     # Creates packages/web/dist/
```

### 2. Sync to Pi

Using rsync (recommended, faster for updates):

```bash
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' \
  packages/server/ pi@pollipi1.local:~/pollipi_timelapse/packages/server/

rsync -avz \
  dist/pollipi_api_server.py pi@pollipi1.local:~/pollipi_timelapse/

rsync -avz --delete \
  packages/web/dist/ pi@pollipi1.local:~/pollipi_timelapse/web/dist/

scp systemd/pollipi.service \
  pi@pollipi1.local:~/.config/systemd/user/
```

Or using scp:

```bash
scp -r packages/server pi@pollipi1.local:~/pollipi_timelapse/
scp dist/pollipi_api_server.py pi@pollipi1.local:~/pollipi_timelapse/
scp -r packages/web/dist pi@pollipi1.local:~/pollipi_timelapse/web/
scp systemd/pollipi.service pi@pollipi1.local:~/.config/systemd/user/
```

### 3. SSH to the Pi and install dependencies

```bash
ssh pi@pollipi1.local
```

Then on the Pi:

```bash
# Create required directories
mkdir -p ~/pollipi_timelapse/images
mkdir -p ~/.config/systemd/user

# Install dependencies
cd ~/pollipi_timelapse/packages/server
pip install -e . --break-system-packages

# Reload systemd
systemctl --user daemon-reload
systemctl --user enable pollipi.service
systemctl --user restart pollipi.service
```

### 4. Health check

```bash
# Check service status
systemctl --user status pollipi.service

# Test the API
curl http://localhost:8000/device
curl http://localhost:8000/status
```

## Troubleshooting

### SSH Connection Issues

**Problem:** `Cannot connect to pollipi1.local`

**Solutions:**
- Check Pi hostname: `hostname -I` on the Pi
- Use IP address instead: `./scripts/deploy_pi.sh -h 192.168.1.100 -u pi`
- Verify SSH is enabled: `sudo systemctl status ssh` on the Pi
- Add SSH public key: `ssh-copy-id pi@pollipi1.local`

### Deployment Script Hangs

**Problem:** Script appears frozen

**Solutions:**
- Press Ctrl+C to cancel and retry
- Check Pi network connectivity: `ping pollipi1.local`
- Verify rsync is installed: `rsync --version`
- Try with `-p 22` to explicitly set SSH port

### Service Fails to Start

**Problem:** `systemctl status pollipi.service` shows failed or inactive

**Solutions:**

1. Check service logs:
   ```bash
   journalctl --user -u pollipi.service -n 50
   journalctl --user -u pollipi.service -f  # Follow logs
   ```

2. Check Python dependencies:
   ```bash
   cd ~/pollipi_timelapse/packages/server
   pip list
   pip install -e . --break-system-packages
   ```

3. Manually start for debugging:
   ```bash
   cd ~/pollipi_timelapse
   python3 pollipi_api_server.py
   ```

### API Not Responding

**Problem:** `curl http://localhost:8000/device` times out or fails

**Solutions:**

1. Check if service is running:
   ```bash
   systemctl --user status pollipi.service
   ```

2. Wait for startup (can take 10-20 seconds on first start):
   ```bash
   sleep 5 && curl http://localhost:8000/device
   ```

3. Check if port 8000 is listening:
   ```bash
   netstat -tuln | grep 8000
   ```

4. Check firewall (if configured):
   ```bash
   sudo ufw allow 8000/tcp
   ```

### Web UI Not Accessible

**Problem:** Browser shows 404 or empty page at `http://pollipi1.local:8000/app/`

**Solutions:**

1. Check if web files were synced:
   ```bash
   ls -la ~/pollipi_timelapse/web/dist/
   ```

2. Rebuild web on development machine:
   ```bash
   pnpm build:web
   ```

3. Redeploy using the script:
   ```bash
   ./scripts/deploy_pi.sh -h pollipi1.local -u pi
   ```

## Viewing Logs

View real-time service logs:

```bash
# On the Pi
journalctl --user -u pollipi.service -f

# Or remotely
ssh pi@pollipi1.local journalctl --user -u pollipi.service -f
```

View last N lines:

```bash
journalctl --user -u pollipi.service -n 100
```

Filter by error level:

```bash
journalctl --user -u pollipi.service -p err
```

## Production Checklist

Before treating the deployment as production-ready:

- [ ] Camera tested with `rpicam-hello`
- [ ] Pi running latest Raspberry Pi OS
- [ ] Python 3.11+ installed
- [ ] SSH public key configured for passwordless auth
- [ ] Deployment script runs successfully with no errors
- [ ] Health check passes: `curl http://pollipi1.local:8000/device`
- [ ] Web UI accessible: `http://pollipi1.local:8000/app/`
- [ ] Service running: `systemctl --user status pollipi.service`
- [ ] Logs show no errors: `journalctl --user -u pollipi.service`
- [ ] Pi set to auto-start service at boot (systemd user services auto-start by default)

## Security Considerations

- **SSH keys**: Use SSH public key authentication instead of passwords
- **Network isolation**: Keep Pi on a private, trusted network
- **Firewall**: Restrict port 8000 to your local network
- **Service limitations**: The systemd service has security hardening:
  - NoNewPrivileges=true
  - ProtectSystem=strict
  - ProtectHome=yes
  - Read-only filesystem except for working directory

## Multi-Device Deployment

To deploy to multiple Pis:

### Linux/macOS/WSL

```bash
for DEVICE in pollipi1 pollipi2 pollipi3; do
  echo "Deploying to $DEVICE..."
  ./scripts/deploy_pi.sh -h "$DEVICE.local" -u pi -d "$DEVICE"
done
```

### Windows PowerShell

```powershell
@("pollipi1", "pollipi2", "pollipi3") | ForEach-Object {
  Write-Host "Deploying to $_..."
  .\scripts\deploy_pi.ps1 -HostName "$_.local" -UserName pi -DeviceId $_
}
```

## Next Steps

After successful deployment:

1. **Camera setup** — See [QUICKSTART.md](../QUICKSTART.md) — Step 4
2. **Configure device** — Set device ID, display name, camera profile
3. **Test recording** — Verify camera can capture images
4. **Deploy to fleet** — Use the multi-device deployment method above

For more information, see:
- [QUICKSTART.md](../QUICKSTART.md) — Quick start guide
- [DEVICE_ONBOARDING.md](../DEVICE_ONBOARDING.md) — Multi-device setup
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) — Common issues
