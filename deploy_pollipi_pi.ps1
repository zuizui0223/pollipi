# PolliPi Deployment Script for Windows/WSL
# 
# This script deploys PolliPi from a development machine to a Raspberry Pi.
# It copies the necessary files and runs the installation scripts via SSH/SCP.
#
# Prerequisites:
#   - SSH access to the Raspberry Pi (ssh-key or password auth configured)
#   - SCP available (usually comes with OpenSSH)
#   - Build artifact: dist/pollipi_api_server.py (run: pnpm build:server)
#
# Usage examples:
#   .\deploy_pollipi_pi.ps1 -HostName pi@pollipi1.local
#   .\deploy_pollipi_pi.ps1 -HostName pi@pollipi2.local -DeviceId pollipi2
#   .\deploy_pollipi_pi.ps1 -HostName 192.168.1.25 -User pi -DeviceId pollipi1

param(
    [Parameter(Mandatory=$true, HelpMessage="SSH target (e.g., pi@pollipi1.local or user@192.168.1.25)")]
    [string]$HostName,
    
    [Parameter(Mandatory=$false, HelpMessage="Username if not included in HostName")]
    [string]$User,
    
    [Parameter(Mandatory=$false, HelpMessage="Device ID to configure (optional)")]
    [string]$DeviceId,
    
    [Parameter(Mandatory=$false, HelpMessage="Path to dist directory")]
    [string]$DistDir = "dist",
    
    [Parameter(Mandatory=$false, HelpMessage="Suppress SCP prompts")]
    [switch]$Force
)

# Configuration
$ErrorActionPreference = "Stop"
$PSDefaultParameterValues['Out-Default:OutVariable'] = 'null'

Write-Host "=== PolliPi Deployment Script ===" -ForegroundColor Cyan
Write-Host ""

# Parse SSH target
$SshTarget = $HostName
if ($User -and -not $HostName.Contains("@")) {
    $SshTarget = "$User@$HostName"
}

Write-Host "Target: $SshTarget" -ForegroundColor White
if ($DeviceId) {
    Write-Host "Device ID: $DeviceId" -ForegroundColor Gray
}
Write-Host ""

# Validate build artifact exists
$DistArtifact = Join-Path $DistDir "pollipi_api_server.py"
if (-not (Test-Path $DistArtifact)) {
    Write-Host "ERROR: Build artifact not found at: $DistArtifact" -ForegroundColor Red
    Write-Host "Please build first with: pnpm build:server" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found build artifact: $DistArtifact" -ForegroundColor Green

# Validate deployment scripts exist
$InstallScript = "install.sh"
$SetupScript = "setup_device.sh"

if (-not (Test-Path $InstallScript)) {
    Write-Host "ERROR: $InstallScript not found" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $SetupScript)) {
    Write-Host "ERROR: $SetupScript not found" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found deployment scripts" -ForegroundColor Green
Write-Host ""

# Copy files to remote
Write-Host "Copying files to $SshTarget..." -ForegroundColor Cyan

$Files = @(
    @{ Local = $DistArtifact; Remote = "pollipi_api_server.py" },
    @{ Local = $InstallScript; Remote = "install.sh" },
    @{ Local = $SetupScript; Remote = "setup_device.sh" }
)

foreach ($file in $Files) {
    $local = $file.Local
    $remote = $file.Remote
    
    Write-Host "  Copying $remote..." -ForegroundColor Gray
    
    $scpCmd = @("scp", "-r", $local, "$($SshTarget):~/$remote")
    
    try {
        & $scpCmd.Item(0) $scpCmd[1..($scpCmd.Length-1)] 2>&1 | Out-Null
    }
    catch {
        Write-Host "  ERROR: Failed to copy $remote" -ForegroundColor Red
        Write-Host "  Make sure SSH key is configured or password auth is available" -ForegroundColor Yellow
        exit 1
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: SCP failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ Files copied successfully" -ForegroundColor Green
Write-Host ""

# Run install script
Write-Host "Running install.sh on the Pi..." -ForegroundColor Cyan

$sshCmd = @("ssh", $SshTarget, "bash ~/install.sh")
try {
    & $sshCmd.Item(0) $sshCmd[1..($sshCmd.Length-1)]
}
catch {
    Write-Host "ERROR: SSH command failed" -ForegroundColor Red
    exit 1
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: install.sh failed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Installation script completed" -ForegroundColor Green
Write-Host ""

# Run setup script if device ID provided
if ($DeviceId) {
    Write-Host "Running setup_device.sh with device ID: $DeviceId" -ForegroundColor Cyan
    
    $setupCmd = @("ssh", $SshTarget, "bash ~/setup_device.sh $DeviceId")
    try {
        & $setupCmd.Item(0) $setupCmd[1..($setupCmd.Length-1)]
    }
    catch {
        Write-Host "WARNING: setup_device.sh may need manual interaction" -ForegroundColor Yellow
        Write-Host "SSH to the Pi and run: bash ~/setup_device.sh $DeviceId" -ForegroundColor Yellow
    }
} else {
    Write-Host "Next step: Configure the device profile" -ForegroundColor Yellow
    Write-Host "  ssh $SshTarget 'bash ~/setup_device.sh [device_id]'" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Verify installation:" -ForegroundColor Gray
Write-Host "  ssh $SshTarget 'curl http://localhost:8000/device'" -ForegroundColor Gray
Write-Host "  ssh $SshTarget 'curl http://localhost:8000/status'" -ForegroundColor Gray
Write-Host ""
Write-Host "View service logs:" -ForegroundColor Gray
Write-Host "  ssh $SshTarget 'journalctl --user -u pollipi.service -f'" -ForegroundColor Gray
