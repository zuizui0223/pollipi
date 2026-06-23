#!/bin/bash
set -eu

# PolliPi Device Configuration Script
# Sets up camera profile, configuration, and systemd service for a Raspberry Pi.
#
# Usage: bash setup_device.sh [device_id]
#
# If device_id is not provided, it will be derived from the hostname.
# The script will prompt for camera type selection.

DEVICE_ID="${1:-}"
POLLIPI_HOME="${HOME}/pollipi_timelapse"
CONFIG_DIR="${HOME}/.config/pollipi"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

# Ensure required directories exist
mkdir -p "$CONFIG_DIR"
mkdir -p "$SYSTEMD_USER_DIR"

echo "=== PolliPi Device Configuration ==="
echo ""

# Determine device ID
if [ -z "$DEVICE_ID" ]; then
    DEVICE_ID=$(hostname)
    echo "Device ID not provided, using hostname: $DEVICE_ID"
else
    echo "Device ID: $DEVICE_ID"
fi

# Select camera profile
echo ""
echo "Select your camera module:"
echo "  1. Camera Module 3 Wide"
echo "  2. Camera Module 3 NoIR Wide"
echo "  3. Raspberry Pi AI Camera"
echo ""

CAMERA_PROFILE=""
while [ -z "$CAMERA_PROFILE" ]; do
    read -p "Enter camera choice (1-3): " CHOICE
    case "$CHOICE" in
        1)
            CAMERA_PROFILE="module3_wide"
            echo "Selected: Camera Module 3 Wide"
            ;;
        2)
            CAMERA_PROFILE="module3_nir_wide"
            echo "Selected: Camera Module 3 NoIR Wide"
            ;;
        3)
            CAMERA_PROFILE="ai_camera"
            echo "Selected: Raspberry Pi AI Camera"
            ;;
        *)
            echo "Invalid choice. Please enter 1, 2, or 3."
            ;;
    esac
done

# Optionally set a display name
echo ""
read -p "Enter a display name for this device (or press Enter to use device ID): " DISPLAY_NAME
DISPLAY_NAME="${DISPLAY_NAME:-$DEVICE_ID}"

echo ""
echo "Creating configuration..."

# Generate configuration file
CONFIG_FILE="$CONFIG_DIR/config.json"

cat > "$CONFIG_FILE" << EOF
{
  "device_id": "$DEVICE_ID",
  "display_name": "$DISPLAY_NAME",
  "camera_profile": "$CAMERA_PROFILE",
  "api_host": "0.0.0.0",
  "api_port": 8000,
  "image_directory": "$POLLIPI_HOME/images"
}
EOF

echo "✓ Configuration file created: $CONFIG_FILE"

# Create systemd service file
SERVICE_FILE="$SYSTEMD_USER_DIR/pollipi.service"
SERVICE_TEMPLATE="/dev/stdin"

# Read the template from the repo if it exists, otherwise use inline template
if [ -f "$POLLIPI_HOME/../tools/pollipi.service.template" ]; then
    SERVICE_TEMPLATE="$POLLIPI_HOME/../tools/pollipi.service.template"
elif [ -f "$POLLIPI_HOME/pollipi.service.template" ]; then
    SERVICE_TEMPLATE="$POLLIPI_HOME/pollipi.service.template"
fi

# If we have a template file, use it; otherwise create inline
if [ "$SERVICE_TEMPLATE" != "/dev/stdin" ] && [ -f "$SERVICE_TEMPLATE" ]; then
    sed "s|POLLIPI_HOME|$POLLIPI_HOME|g; s|CONFIG_FILE|$CONFIG_FILE|g; s|DEVICE_ID|$DEVICE_ID|g" "$SERVICE_TEMPLATE" > "$SERVICE_FILE"
else
    # Create inline service file
    cat > "$SERVICE_FILE" << 'SERVICE_EOF'
[Unit]
Description=PolliPi API Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 %h/pollipi_timelapse/pollipi_api_server.py
WorkingDirectory=%h/pollipi_timelapse
Environment="PYTHONUNBUFFERED=1"
Restart=on-failure
RestartSec=10

# Runtime directories
RuntimeDirectory=pollipi
StateDirectory=pollipi

# Security
NoNewPrivileges=true
PrivateTmp=true

# Resource limits (adjust as needed)
CPUQuota=75%
MemoryLimit=512M

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pollipi

[Install]
WantedBy=default.target
SERVICE_EOF
fi

echo "✓ Systemd service file created: $SERVICE_FILE"

# Reload systemd daemon
echo ""
echo "Enabling systemd service..."
systemctl --user daemon-reload

# Enable the service
systemctl --user enable pollipi.service

# Start the service
systemctl --user start pollipi.service

echo "✓ Service enabled and started"

# Wait a moment for the service to start
sleep 2

# Check service status
echo ""
echo "Service status:"
systemctl --user status pollipi.service || true

echo ""
echo "=== Configuration Complete ==="
echo ""
echo "Device ID: $DEVICE_ID"
echo "Camera Profile: $CAMERA_PROFILE"
echo "Config file: $CONFIG_FILE"
echo "Service file: $SERVICE_FILE"
echo ""
echo "To view service logs:"
echo "  journalctl --user -u pollipi.service -f"
echo ""
echo "To test the API:"
echo "  curl http://localhost:8000/device"
echo "  curl http://localhost:8000/status"
