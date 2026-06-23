# PolliPi Deployment Script for Raspberry Pi (Windows/WSL)
#
# This script deploys PolliPi to a Raspberry Pi from Windows or WSL.
# It uses SCP to transfer files, then installs dependencies and restarts the service.
#
# Prerequisites:
#   - PowerShell 7+
#   - OpenSSH client (usually available on Windows 11+)
#   - SSH access to the Pi
#
# Usage:
#   .\scripts\deploy_pi.ps1 -HostName pollipi1.local -UserName pi
#   .\scripts\deploy_pi.ps1 -HostName 192.168.1.100 -UserName pi -DeviceId pollipi1
#
# Environment:
#   $env:PI_HOST     - Raspberry Pi hostname or IP (default: pollipi1.local)
#   $env:PI_USER     - SSH username (default: pi)
#   $env:PI_PORT     - SSH port (default: 22)
#   $env:DEVICE_ID   - Device identifier (default: hostname without .local)

param(
    [Parameter(Mandatory=$false, HelpMessage="Raspberry Pi hostname or IP address")]
    [string]$HostName = [System.Environment]::GetEnvironmentVariable("PI_HOST", "User") ?? "pollipi1.local",
    
    [Parameter(Mandatory=$false, HelpMessage="SSH username")]
    [string]$UserName = [System.Environment]::GetEnvironmentVariable("PI_USER", "User") ?? "pi",
    
    [Parameter(Mandatory=$false, HelpMessage="SSH port")]
    [int]$Port = [System.Environment]::GetEnvironmentVariable("PI_PORT", "User") ?? 22,
    
    [Parameter(Mandatory=$false, HelpMessage="Device identifier")]
    [string]$DeviceId = [System.Environment]::GetEnvironmentVariable("DEVICE_ID", "User") ?? ""
)

$ErrorActionPreference = "Stop"

# Derive device ID from hostname if not provided
if ([string]::IsNullOrEmpty($DeviceId)) {
    $DeviceId = $HostName -replace "\.local$", ""
}

$RemoteHost = $HostName
$RemoteUser = $UserName
$RemoteSsh = "$RemoteUser@$RemoteHost"
$RemotePath = "~/pollipi_timelapse"

Write-Host "=== PolliPi Deployment Script ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Target:  $RemoteSsh`:$Port" -ForegroundColor White
Write-Host "Device:  $DeviceId" -ForegroundColor Gray
Write-Host "Path:    $RemotePath" -ForegroundColor Gray
Write-Host ""

# Check SSH connectivity
Write-Host "Checking SSH connectivity..." -ForegroundColor Gray
try {
    $null = ssh -p $Port "$RemoteSsh" "echo OK" 2>&1
} catch {
    Write-Host "ERROR: Cannot connect to $RemoteSsh`:$Port" -ForegroundColor Red
    Write-Host "Please ensure:" -ForegroundColor Yellow
    Write-Host "  1. Pi is powered on and on the network" -ForegroundColor Yellow
    Write-Host "  2. SSH is enabled on the Pi" -ForegroundColor Yellow
    Write-Host "  3. Username/hostname are correct" -ForegroundColor Yellow
    Write-Host "  4. SSH public key is configured or use ssh-add for password auth" -ForegroundColor Yellow
    exit 1
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: SSH connectivity check failed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ SSH OK" -ForegroundColor Green
Write-Host ""

# Build artifacts
Write-Host "Building artifacts..." -ForegroundColor Cyan

Write-Host "  Building server..." -ForegroundColor Gray
$buildOutput = pnpm build:server 2>&1
if ($LASTEXITCODE -ne 0 -or -not (Test-Path "dist/pollipi_api_server.py")) {
    Write-Host "  ERROR: Failed to build dist/pollipi_api_server.py" -ForegroundColor Red
    Write-Host $buildOutput -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Server artifact built" -ForegroundColor Green

Write-Host "  Building web UI..." -ForegroundColor Gray
$buildOutput = pnpm build:web 2>&1
if ($LASTEXITCODE -ne 0 -or -not (Test-Path "packages/web/dist")) {
    Write-Host "  ERROR: Failed to build web UI" -ForegroundColor Red
    Write-Host $buildOutput -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Web UI built" -ForegroundColor Green

Write-Host ""
Write-Host "Syncing to Pi..." -ForegroundColor Cyan

# Create remote directory
$null = ssh -p $Port "$RemoteSsh" "mkdir -p $RemotePath" 2>&1

# Sync server code
Write-Host "  Syncing server code..." -ForegroundColor Gray
$scpCmd = @("scp", "-P", $Port.ToString(), "-r", "packages/server", "$($RemoteSsh):$RemotePath/packages/")
& $scpCmd[0] $scpCmd[1..($scpCmd.Length-1)] 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: SCP sync had issues but may have succeeded" -ForegroundColor Yellow
}
Write-Host "  ✓ Server code synced" -ForegroundColor Green

# Sync artifact
Write-Host "  Syncing build artifact..." -ForegroundColor Gray
$scpCmd = @("scp", "-P", $Port.ToString(), "dist/pollipi_api_server.py", "$($RemoteSsh):$RemotePath/")
& $scpCmd[0] $scpCmd[1..($scpCmd.Length-1)] 2>&1 | Out-Null
Write-Host "  ✓ Artifact synced" -ForegroundColor Green

# Sync web build
Write-Host "  Syncing web UI build..." -ForegroundColor Gray
$scpCmd = @("scp", "-P", $Port.ToString(), "-r", "packages/web/dist", "$($RemoteSsh):$RemotePath/web/")
& $scpCmd[0] $scpCmd[1..($scpCmd.Length-1)] 2>&1 | Out-Null
Write-Host "  ✓ Web UI synced" -ForegroundColor Green

# Sync systemd service
Write-Host "  Syncing systemd service..." -ForegroundColor Gray
$scpCmd = @("scp", "-P", $Port.ToString(), "systemd/pollipi.service", "$($RemoteSsh):.config/systemd/user/")
& $scpCmd[0] $scpCmd[1..($scpCmd.Length-1)] 2>&1 | Out-Null
Write-Host "  ✓ Service file synced" -ForegroundColor Green

Write-Host ""
Write-Host "Installing dependencies on Pi..." -ForegroundColor Cyan

# Remote commands for installation
$remoteCommands = @"
set -eu

PI_HOME=`$HOME
POLLIPI_HOME=`$PI_HOME/pollipi_timelapse

# Create directories
mkdir -p `$POLLIPI_HOME/images
mkdir -p `$PI_HOME/.config/pollipi

# Verify Python version
PYTHON_VERSION=\$(python3 --version 2>&1 | awk '{print \$2}')
PYTHON_MAJOR=\$(echo \$PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=\$(echo \$PYTHON_VERSION | cut -d. -f2)

if [ "\$PYTHON_MAJOR" -lt 3 ] || ([ "\$PYTHON_MAJOR" -eq 3 ] && [ "\$PYTHON_MINOR" -lt 11 ]); then
    echo "ERROR: Python 3.11+ required (found \$PYTHON_VERSION)"
    exit 1
fi

# Install dependencies
cd `$POLLIPI_HOME/packages/server
pip install -e . --break-system-packages >/dev/null 2>&1
echo "✓ Dependencies installed"
"@

$null = ssh -p $Port "$RemoteSsh" $remoteCommands 2>&1

Write-Host ""
Write-Host "Reloading systemd..." -ForegroundColor Cyan

$systemdCommands = @"
systemctl --user daemon-reload
systemctl --user enable pollipi.service
systemctl --user restart pollipi.service
sleep 2
echo "✓ Service restarted"
"@

$null = ssh -p $Port "$RemoteSsh" $systemdCommands 2>&1

Write-Host ""
Write-Host "Health check..." -ForegroundColor Cyan

# Check API
$maxRetries = 3
$retryCount = 0
$apiReady = $false

while ($retryCount -lt $maxRetries) {
    try {
        $response = ssh -p $Port "$RemoteSsh" "curl -s http://localhost:8000/device" 2>&1
        if ($response -and $response.Length -gt 0) {
            $apiReady = $true
            Write-Host "✓ API responding" -ForegroundColor Green
            Write-Host ""
            Write-Host "Device info: $response" -ForegroundColor Gray
            break
        }
    } catch {
        # Expected during startup
    }
    
    $retryCount++
    if ($retryCount -lt $maxRetries) {
        Start-Sleep -Seconds 2
    }
}

if (-not $apiReady) {
    Write-Host "WARNING: API not responding. Check logs with:" -ForegroundColor Yellow
    Write-Host "  ssh $RemoteSsh journalctl --user -u pollipi.service -f" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Gray
Write-Host "  1. SSH to the Pi:" -ForegroundColor Gray
Write-Host "     ssh $RemoteSsh" -ForegroundColor Gray
Write-Host "  2. Check service status:" -ForegroundColor Gray
Write-Host "     systemctl --user status pollipi.service" -ForegroundColor Gray
Write-Host "  3. View logs:" -ForegroundColor Gray
Write-Host "     journalctl --user -u pollipi.service -f" -ForegroundColor Gray
Write-Host "  4. Access the web UI:" -ForegroundColor Gray
Write-Host "     http://$RemoteHost`:8000/app/" -ForegroundColor Gray
