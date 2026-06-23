#!/bin/bash
# Quick web-only deployment to Raspberry Pi
#
# Usage:
#   ./scripts/deploy_web_only.sh [-h HOST] [-u USER] [-p PORT]
#
# Examples:
#   ./scripts/deploy_web_only.sh -h pollipi1.local -u pi
#   PI_HOST=192.168.1.100 ./scripts/deploy_web_only.sh
#
# Environment:
#   PI_HOST - Raspberry Pi hostname or IP (default: pollipi1.local)
#   PI_USER - SSH username (default: pi)
#   PI_PORT - SSH port (default: 22)

set -eu

PI_HOST="${PI_HOST:-pollipi1.local}"
PI_USER="${PI_USER:-pi}"
PI_PORT="${PI_PORT:-22}"

# Parse arguments
while getopts "h:u:p:" opt; do
    case $opt in
        h) PI_HOST="$OPTARG" ;;
        u) PI_USER="$OPTARG" ;;
        p) PI_PORT="$OPTARG" ;;
        *)
            echo "Usage: $0 [-h HOST] [-u USER] [-p PORT]"
            exit 1
            ;;
    esac
done

REMOTE_SSH="${PI_USER}@${PI_HOST}"
REMOTE_PATH="~/pollipi_timelapse/web/dist/"

echo "=========================================="
echo "PolliPi Web UI Deployment"
echo "=========================================="

# Check if packages/web/dist exists
if [ ! -d "packages/web/dist" ]; then
    echo "Build not found. Building web UI..."
    pnpm build:web
fi

echo "Syncing to Pi: $REMOTE_SSH"
echo "  Source: $(pwd)/packages/web/dist/"
echo "  Target: $REMOTE_PATH"
echo ""

# Check connectivity
if ! ssh -p "$PI_PORT" "$REMOTE_SSH" "true" 2>/dev/null; then
    echo "ERROR: Cannot connect to $REMOTE_SSH on port $PI_PORT"
    echo "  Check hostname/IP, username, and SSH access"
    exit 1
fi

echo "✓ Connected to Pi"
echo ""

# Ensure target directory exists
ssh -p "$PI_PORT" "$REMOTE_SSH" "mkdir -p ~/pollipi_timelapse/web/dist/"

# Sync
if rsync -avz --delete -e "ssh -p $PI_PORT" packages/web/dist/ "$REMOTE_SSH:$REMOTE_PATH"; then
    echo ""
    echo "=========================================="
    echo "✓ Deployment complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Open iPad browser: http://$PI_HOST:8000/app/"
    echo "  2. Hard refresh (Cmd+Shift+R on Mac, Ctrl+Shift+R on Linux)"
    echo ""
    echo "For continuous development:"
    echo "  ./scripts/watch_web_and_sync.sh -h $PI_HOST -u $PI_USER"
    echo "=========================================="
else
    echo ""
    echo "ERROR: Sync failed. Check network and Pi connection."
    exit 1
fi
