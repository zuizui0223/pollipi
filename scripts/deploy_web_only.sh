#!/bin/bash
# Quick web-only deployment to a SINGLE Raspberry Pi (dev helper).
#
# For fleet deployment, use pollipi_fleet_deploy.py instead:
#   python3 tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --web-only --execute --confirm-live-deploy
#
# Usage:
#   ./scripts/deploy_web_only.sh -h HOST -u USER [-p PORT]
#
# Examples:
#   ./scripts/deploy_web_only.sh -h zuizui.local -u zuizui0223
#   ./scripts/deploy_web_only.sh -h 192.168.11.10 -u zuizui0223 -p 22
#
# Both -h and -u are REQUIRED. There are no defaults.

set -eu

PI_HOST=""
PI_USER=""
PI_PORT="${PI_PORT:-22}"

# Parse arguments
while getopts "h:u:p:" opt; do
    case $opt in
        h) PI_HOST="$OPTARG" ;;
        u) PI_USER="$OPTARG" ;;
        p) PI_PORT="$OPTARG" ;;
        *)
            echo "Usage: $0 -h HOST -u USER [-p PORT]"
            exit 1
            ;;
    esac
done

if [ -z "$PI_HOST" ] || [ -z "$PI_USER" ]; then
    echo "ERROR: Both -h HOST and -u USER are required."
    echo "Usage: $0 -h HOST -u USER [-p PORT]"
    echo ""
    echo "For fleet deployment, use:"
    echo "  python3 tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --web-only --execute --confirm-live-deploy"
    exit 1
fi

REMOTE_SSH="${PI_USER}@${PI_HOST}"

# Resolve the remote web path from fleet config (default to standard path)
REMOTE_PATH="/home/${PI_USER}/pollipi_timelapse/web/"

# ── Safety guard: reject dangerous rsync --delete targets ──
validate_rsync_target() {
    local target="$1"
    if [ -z "$target" ]; then
        echo "ERROR: Remote path is empty. Aborting."
        exit 1
    fi
    case "$target" in
        /|/home|/home/|"$HOME"|"$HOME/")
            echo "ERROR: Remote path '$target' is a system directory. Aborting."
            exit 1
            ;;
    esac
    # Must be inside pollipi_timelapse
    if ! echo "$target" | grep -q "pollipi_timelapse"; then
        echo "ERROR: Remote path '$target' is outside the PolliPi web directory. Aborting."
        exit 1
    fi
}

validate_rsync_target "$REMOTE_PATH"

echo "=========================================="
echo "PolliPi Web UI Deployment (single Pi)"
echo "=========================================="

# Check if packages/web/dist exists
if [ ! -d "packages/web/dist" ]; then
    echo "Build not found. Building web UI..."
    pnpm build:web
fi

echo "Syncing to Pi: $REMOTE_SSH"
echo "  Source: $(pwd)/packages/web/dist/"
echo "  Target: $REMOTE_SSH:$REMOTE_PATH"
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
ssh -p "$PI_PORT" "$REMOTE_SSH" "mkdir -p ${REMOTE_PATH}"

# Sync
if rsync -avz --delete -e "ssh -p $PI_PORT" packages/web/dist/ "$REMOTE_SSH:$REMOTE_PATH"; then
    echo ""
    echo "=========================================="
    echo "✓ Deployment complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Open iPad Safari: http://$PI_HOST:8000/app/"
    echo "  2. To force refresh: tap and hold the reload button, or close"
    echo "     Safari completely and reopen the URL."
    echo "     You can also append a cache-busting query string:"
    echo "       http://$PI_HOST:8000/app/?v=$(date +%s)"
    echo ""
    echo "For fleet deployment:"
    echo "  python3 tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --web-only --execute --confirm-live-deploy"
    echo "=========================================="
else
    echo ""
    echo "ERROR: Sync failed. Check network and Pi connection."
    exit 1
fi
