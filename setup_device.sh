#!/bin/bash
# PolliPi device setup script
# Run this on the Raspberry Pi after install.sh.
# Usage: bash setup_device.sh [device_id]
#   device_id: optional, defaults to hostname (e.g. pollipi1)
set -e

DEVICE_ID="${1:-$(hostname)}"
INSTALL_DIR="${POLLIPI_INSTALL_DIR:-${HOME}/pollipi_timelapse}"
SERVICE_D="/etc/systemd/system/pollipi.service.d"
USER_NAME="$(whoami)"

echo "=== PolliPi device setup ==="
echo "Device ID will be: ${DEVICE_ID}"
echo ""

echo "Select camera type:"
echo "  1) Camera Module 3 Wide (imx708_wide)      — standard daylight"
echo "  2) Camera Module 3 NoIR Wide (imx708_noir_wide) — IR-capable"
echo "  3) Raspberry Pi AI Camera (imx500)"
read -rp "Choice [1-3]: " choice

case "$choice" in
  1)
    CAMERA_LABEL="Module 3 Wide"
    CAMERA_MODEL="imx708_wide"
    CAMERA_PROFILE="module3_wide_daylight"
    IS_AI="false"; IS_NOIR="false"; IS_WIDE="true"
    ;;
  2)
    CAMERA_LABEL="Module 3 NoIR Wide"
    CAMERA_MODEL="imx708_noir_wide"
    CAMERA_PROFILE="module3_noir_wide_ir"
    IS_AI="false"; IS_NOIR="true"; IS_WIDE="true"
    ;;
  3)
    CAMERA_LABEL="AI Camera"
    CAMERA_MODEL="imx500"
    CAMERA_PROFILE="ai_camera_daylight"
    IS_AI="true"; IS_NOIR="false"; IS_WIDE="false"
    ;;
  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

read -rp "Device display name shown in PWA [${DEVICE_ID}]: " DEVICE_NAME
DEVICE_NAME="${DEVICE_NAME:-${DEVICE_ID}}"

echo ""
echo "--- Writing systemd service ---"
sudo tee /etc/systemd/system/pollipi.service >/dev/null <<EOF
[Unit]
Description=PolliPi Field Observer API
After=network-online.target
Wants=network-online.target

[Service]
User=${USER_NAME}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/.venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 3
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "--- Writing camera profile ---"
sudo mkdir -p "${SERVICE_D}"
sudo tee "${SERVICE_D}/camera-profile.conf" >/dev/null <<EOF
[Service]
Environment=POLLIPI_DEVICE_ID=${DEVICE_ID}
Environment="POLLIPI_DEVICE_NAME=${DEVICE_NAME}"
Environment="POLLIPI_CAMERA_LABEL=${CAMERA_LABEL}"
Environment=POLLIPI_CAMERA_MODEL=${CAMERA_MODEL}
Environment=POLLIPI_CAMERA_PROFILE=${CAMERA_PROFILE}
Environment=POLLIPI_IS_AI_CAMERA=${IS_AI}
Environment=POLLIPI_IS_NOIR=${IS_NOIR}
Environment=POLLIPI_IS_WIDE=${IS_WIDE}
EOF

echo "--- Enabling and starting pollipi service ---"
sudo systemctl daemon-reload
sudo systemctl enable --now pollipi.service
sudo systemctl restart pollipi.service
sleep 2

echo ""
echo "=== Setup complete ==="
echo "Device ID:   ${DEVICE_ID}"
echo "Device name: ${DEVICE_NAME}"
echo "Camera:      ${CAMERA_LABEL} (${CAMERA_MODEL})"
echo "Profile:     ${CAMERA_PROFILE}"
echo ""
echo "Verify:"
echo "  curl http://localhost:8000/device"
echo "  curl http://localhost:8000/status"
echo ""
echo "PWA (open from iPad/browser on the same network):"
echo "  http://$(hostname).local:8000/app/"
