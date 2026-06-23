#!/bin/bash
set -eu

# PolliPi Raspberry Pi Installation Script
# This script sets up the environment and dependencies for running PolliPi on a Raspberry Pi.
# 
# Usage: bash install.sh
#
# Prerequisites:
#   - Python 3.11+
#   - Raspberry Pi OS Bookworm (recommended)
#   - Internet connection

echo "=== PolliPi Installation Script ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "ERROR: Python 3.11+ is required (found Python $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION found"

# Create directory structure
POLLIPI_HOME="${HOME}/pollipi_timelapse"
mkdir -p "$POLLIPI_HOME"
mkdir -p "$POLLIPI_HOME/images"
mkdir -p "$POLLIPI_HOME/config"
mkdir -p "${HOME}/.config/systemd/user"
mkdir -p "${HOME}/.config/pollipi"

echo "✓ Created directories:"
echo "  - $POLLIPI_HOME"
echo "  - $POLLIPI_HOME/images"
echo "  - $POLLIPI_HOME/config"
echo "  - ${HOME}/.config/systemd/user"
echo "  - ${HOME}/.config/pollipi"

# Check if a Python venv is needed
if [ ! -d "$POLLIPI_HOME/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$POLLIPI_HOME/venv"
    echo "✓ Virtual environment created at $POLLIPI_HOME/venv"
    
    # Activate the venv and upgrade pip
    source "$POLLIPI_HOME/venv/bin/activate"
    python -m pip install --upgrade pip
    echo "✓ pip upgraded"
else
    echo "✓ Virtual environment already exists"
    source "$POLLIPI_HOME/venv/bin/activate"
fi

# Install the pollipi_api_server runtime dependencies
# The server is a single Python file with all dependencies bundled
# Dependencies are embedded in the artifact for deployment
echo "✓ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Run setup_device.sh to configure your camera and device profile"
echo "     bash $POLLIPI_HOME/setup_device.sh"
echo "  2. Verify the service is running:"
echo "     systemctl --user status pollipi"
echo "  3. Test the API:"
echo "     curl http://localhost:8000/device"
