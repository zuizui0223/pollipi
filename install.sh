#!/bin/bash
# PolliPi install script
# Run this on the Raspberry Pi after copying source files.
# Usage: bash install.sh
set -e

INSTALL_DIR="${POLLIPI_INSTALL_DIR:-${HOME}/pollipi_timelapse}"

echo "=== PolliPi install ==="
echo "Install directory: ${INSTALL_DIR}"
echo ""

echo "--- Installing system packages ---"
sudo apt update
sudo apt install -y python3-picamera2 python3-venv python3-fastapi python3-uvicorn

echo "--- Creating directory structure ---"
mkdir -p "${INSTALL_DIR}/images"
cd "${INSTALL_DIR}"

if [ ! -d .venv ]; then
  echo "--- Creating Python virtual environment ---"
  python3 -m venv --system-site-packages .venv
else
  echo "--- Virtual environment already exists, skipping ---"
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next step: run setup_device.sh to configure your camera profile and systemd service."
echo "  bash ${INSTALL_DIR}/setup_device.sh"
