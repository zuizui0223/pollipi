#!/bin/bash
set -eu

# PolliPi Deployment Script for Raspberry Pi
# 
# This script deploys PolliPi to a Raspberry Pi from Linux/macOS/WSL.
# It uses rsync or scp to sync the source code and builds to the Pi,
# then installs dependencies and restarts the service.
#
# Usage:
#   ./scripts/deploy_pi.sh [-h HOST] [-u USER] [-p PORT] [-d DEVICE_ID]
#
# Examples:
#   ./scripts/deploy_pi.sh -h pollipi1.local -u pi
#   ./scripts/deploy_pi.sh -h 192.168.1.100 -u pi -d pollipi1
#
# Environment:
#   PI_HOST    - Raspberry Pi hostname or IP (default: pollipi1.local)
#   PI_USER    - SSH username (default: pi)
#   PI_PORT    - SSH port (default: 22)
#   DEVICE_ID  - Device identifier (default: hostname without .local)

PI_HOST="${PI_HOST:-pollipi1.local}"
PI_USER="${PI_USER:-pi}"
PI_PORT="${PI_PORT:-22}"
DEVICE_ID="${DEVICE_ID:-}"

# Parse arguments
while getopts "h:u:p:d::" opt; do
    case $opt in
        h) PI_HOST="$OPTARG" ;;
        u) PI_USER="$OPTARG" ;;
        p) PI_PORT="$OPTARG" ;;
        d) DEVICE_ID="$OPTARG" ;;
        *) 
            echo "Usage: $0 [-h HOST] [-u USER] [-p PORT] [-d DEVICE_ID]"
            exit 1
            ;;
    esac
done

# Set device ID from hostname if not provided
if [ -z "$DEVICE_ID" ]; then
    DEVICE_ID="${PI_HOST%.local}"
fi

REMOTE_USER="$PI_USER"
REMOTE_HOST="$PI_HOST"
REMOTE_SSH="$REMOTE_USER@$REMOTE_HOST"
REMOTE_PORT="$PI_PORT"
REMOTE_PATH="~/pollipi_timelapse"

echo "=== PolliPi Deployment Script ==="
echo ""
echo "Target:  $REMOTE_SSH:$REMOTE_PORT"
echo "Device:  $DEVICE_ID"
echo "Path:    $REMOTE_PATH"
echo ""

# Ensure SSH connectivity
echo "Checking SSH connectivity..."
if ! ssh -p "$REMOTE_PORT" "$REMOTE_SSH" "echo ✓ SSH OK" 2>/dev/null; then
    echo "ERROR: Cannot connect to $REMOTE_SSH:$REMOTE_PORT"
    echo "Please ensure:"
    echo "  1. Pi is powered on and on the network"
    echo "  2. SSH is enabled on the Pi"
    echo "  3. Username/hostname are correct"
    exit 1
fi

echo ""
echo "Building artifacts..."

# Build the server artifact
echo "  Building server..."
pnpm build:server >/dev/null 2>&1
if [ ! -f "dist/pollipi_api_server.py" ]; then
    echo "  ERROR: Failed to build dist/pollipi_api_server.py"
    exit 1
fi
echo "  ✓ Server artifact built"

# Build the web UI
echo "  Building web UI..."
pnpm build:web >/dev/null 2>&1
if [ ! -d "packages/web/dist" ]; then
    echo "  ERROR: Failed to build web UI"
    exit 1
fi
echo "  ✓ Web UI built"

echo ""
echo "Syncing to Pi..."

# Create remote directory
ssh -p "$REMOTE_PORT" "$REMOTE_SSH" "mkdir -p $REMOTE_PATH"

# Sync the repository structure
echo "  Syncing source code..."
rsync -avz --delete \
    -e "ssh -p $REMOTE_PORT" \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.pnpm-store' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.venv' \
    --exclude='venv' \
    packages/server/ "$REMOTE_SSH:$REMOTE_PATH/packages/server/" \
    >/dev/null 2>&1
echo "  ✓ Server code synced"

# Sync the artifact
echo "  Syncing build artifact..."
rsync -avz \
    -e "ssh -p $REMOTE_PORT" \
    dist/pollipi_api_server.py "$REMOTE_SSH:$REMOTE_PATH/" \
    >/dev/null 2>&1
echo "  ✓ Artifact synced"

# Sync the web build
echo "  Syncing web UI build..."
rsync -avz --delete \
    -e "ssh -p $REMOTE_PORT" \
    packages/web/dist/ "$REMOTE_SSH:$REMOTE_PATH/web/dist/" \
    >/dev/null 2>&1
echo "  ✓ Web UI synced"

# Sync the systemd service file
echo "  Syncing systemd service..."
scp -P "$REMOTE_PORT" systemd/pollipi.service \
    "$REMOTE_SSH:~/.config/systemd/user/pollipi.service" \
    >/dev/null 2>&1
echo "  ✓ Service file synced"

echo ""
echo "Installing dependencies on Pi..."

# Create required directories and install dependencies
ssh -p "$REMOTE_PORT" "$REMOTE_SSH" bash << 'REMOTE_COMMANDS'
set -eu

PI_HOME="$HOME"
POLLIPI_HOME="$PI_HOME/pollipi_timelapse"

# Create directories
mkdir -p "$POLLIPI_HOME/images"
mkdir -p "$PI_HOME/.config/pollipi"

# Verify Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "ERROR: Python 3.11+ required (found $PYTHON_VERSION)"
    exit 1
fi

# Install dependencies from pyproject.toml
cd "$POLLIPI_HOME/packages/server"
pip install -e . --break-system-packages >/dev/null 2>&1
echo "✓ Dependencies installed"

REMOTE_COMMANDS

echo ""
echo "Reloading systemd..."
ssh -p "$REMOTE_PORT" "$REMOTE_SSH" bash << 'REMOTE_COMMANDS'
systemctl --user daemon-reload
systemctl --user enable pollipi.service
systemctl --user restart pollipi.service
echo "✓ Service restarted"
REMOTE_COMMANDS

echo ""
echo "Health check..."
sleep 2

# Check if the API is responding
if ssh -p "$REMOTE_PORT" "$REMOTE_SSH" "curl -s http://localhost:8000/device >/dev/null 2>&1"; then
    echo "✓ API responding"
    
    # Get device info
    DEVICE_INFO=$(ssh -p "$REMOTE_PORT" "$REMOTE_SSH" "curl -s http://localhost:8000/device")
    echo ""
    echo "Device info: $DEVICE_INFO"
else
    echo "WARNING: API not responding yet. Waiting..."
    sleep 3
    if ssh -p "$REMOTE_PORT" "$REMOTE_SSH" "curl -s http://localhost:8000/device >/dev/null 2>&1"; then
        echo "✓ API responding"
    else
        echo "WARNING: API still not responding. Check logs with:"
        echo "  ssh $REMOTE_SSH journalctl --user -u pollipi.service -f"
    fi
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "  1. SSH to the Pi:"
echo "     ssh $REMOTE_SSH"
echo "  2. Check service status:"
echo "     systemctl --user status pollipi.service"
echo "  3. View logs:"
echo "     journalctl --user -u pollipi.service -f"
echo "  4. Access the web UI:"
echo "     http://$PI_HOST:8000/app/"
