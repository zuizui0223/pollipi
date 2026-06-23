#!/bin/bash
# Watch and auto-sync web UI changes to a SINGLE Raspberry Pi (dev helper).
#
# For fleet deployment, use pollipi_fleet_deploy.py instead:
#   python3 tools/pollipi_fleet_deploy.py --config tools/fleet.local.json --web-only --execute --confirm-live-deploy
#
# Usage:
#   ./scripts/watch_web_and_sync_one_pi.sh -h HOST -u USER [-p PORT]
#
# Examples:
#   ./scripts/watch_web_and_sync_one_pi.sh -h zuizui.local -u zuizui0223
#   ./scripts/watch_web_and_sync_one_pi.sh -h 192.168.11.10 -u zuizui0223 -p 22
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
echo "PolliPi Web UI Auto-Sync Monitor"
echo "=========================================="
echo "Target: $REMOTE_SSH:$REMOTE_PATH"
echo "Watching: packages/web/src/"
echo ""
echo "rsync --delete will sync to: $REMOTE_SSH:$REMOTE_PATH"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

do_build_and_sync() {
    local timestamp
    timestamp="$(date '+%H:%M:%S')"

    echo "[$timestamp] Building web UI..."
    if ! pnpm build:web > /tmp/web_build.log 2>&1; then
        echo "[$timestamp] Build failed"
        tail -10 /tmp/web_build.log
        return 1
    fi
    echo "[$timestamp] ✓ Build complete"

    echo "[$timestamp] Syncing to $REMOTE_SSH..."
    if rsync -avz --delete -e "ssh -p $PI_PORT" packages/web/dist/ "$REMOTE_SSH:$REMOTE_PATH" > /tmp/rsync.log 2>&1; then
        echo "[$timestamp] ✓ Sync complete — iPad will update on next refresh"
    else
        echo "[$timestamp] Sync failed"
        cat /tmp/rsync.log
        return 1
    fi
    echo ""
}

# Check if fswatch is available
if command -v fswatch &> /dev/null; then
    fswatch -r packages/web/src/ | while read -r change; do
        echo "[$(date '+%H:%M:%S')] Change detected: $change"
        do_build_and_sync || true
    done
else
    echo "fswatch not found. Falling back to polling every 3 seconds."
    echo "  To install fswatch:"
    echo "    macOS: brew install fswatch"
    echo "    Linux: apt install fswatch"
    echo ""

    PREV_HASH=""
    while true; do
        CURR_HASH=$(find packages/web/src -type f | sort | xargs md5sum 2>/dev/null | md5sum | awk '{print $1}')
        if [ "$CURR_HASH" != "$PREV_HASH" ] && [ -n "$PREV_HASH" ]; then
            echo "[$(date '+%H:%M:%S')] Change detected"
            do_build_and_sync || true
        fi
        PREV_HASH="$CURR_HASH"
        sleep 3
    done
fi
