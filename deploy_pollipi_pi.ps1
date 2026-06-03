param(
  [Parameter(Mandatory = $true)]
  [string]$HostName,

  [string]$User = "pi",

  [ValidateSet("module3-wide", "module3-noir-wide", "ai-camera")]
  [string]$Preset = "module3-wide",

  [string]$RemoteDir = "",

  [string]$DeviceId = "",

  [switch]$InstallDependencies
)

$ErrorActionPreference = "Stop"

if (-not $RemoteDir) {
  $RemoteDir = "/home/$User/pollipi_timelapse"
}

$profiles = @{
  "module3-wide" = @{
    DeviceName = "Site Module 3"
    CameraLabel = "Module 3 Wide"
    CameraModel = "imx708_wide"
    CameraProfile = "module3_wide_daylight"
    IsAi = "false"
    IsNoir = "false"
    IsWide = "true"
  }
  "module3-noir-wide" = @{
    DeviceName = "Site NoIR"
    CameraLabel = "Module 3 NoIR Wide"
    CameraModel = "imx708_noir_wide"
    CameraProfile = "module3_noir_wide_ir"
    IsAi = "false"
    IsNoir = "true"
    IsWide = "true"
  }
  "ai-camera" = @{
    DeviceName = "Site AI Camera"
    CameraLabel = "AI Camera"
    CameraModel = "imx500"
    CameraProfile = "ai_camera_daylight"
    IsAi = "true"
    IsNoir = "false"
    IsWide = "false"
  }
}

if (-not $env:POLLIPI_DEPLOY_PASSWORD) {
  throw "Set POLLIPI_DEPLOY_PASSWORD before running this script, or configure SSH keys and adapt the script."
}

$profile = $profiles[$Preset]
$resolvedDeviceId = $DeviceId.Trim()
if (-not $resolvedDeviceId) {
  $resolvedDeviceId = ($HostName -replace "\.local$", "")
}
$target = "$User@$HostName"
$sourceFiles = @(
  ".\pollipi_api_server.py",
  ".\README.md",
  ".\QUICKSTART.md",
  ".\DEVICE_ONBOARDING.md",
  ".\TROUBLESHOOTING.md",
  ".\install.sh",
  ".\setup_device.sh",
  ".\imx500_detect_test.py",
  ".\web"
)

foreach ($path in $sourceFiles) {
  if (-not (Test-Path -LiteralPath $path)) {
    throw "Missing source path: $path"
  }
}

$askpass = Join-Path $env:TEMP ("pollipi_askpass_" + [guid]::NewGuid().ToString("N") + ".cmd")
$serviceFile = Join-Path $env:TEMP ("pollipi_service_" + [guid]::NewGuid().ToString("N") + ".service")
$profileFile = Join-Path $env:TEMP ("pollipi_camera_profile_" + [guid]::NewGuid().ToString("N") + ".conf")
$oldAskpass = $env:SSH_ASKPASS
$oldAskpassRequire = $env:SSH_ASKPASS_REQUIRE
$oldDisplay = $env:DISPLAY

try {
  Set-Content -LiteralPath $askpass -Value "@echo off`r`necho %POLLIPI_DEPLOY_PASSWORD%" -Encoding ASCII
  Set-Content -LiteralPath $serviceFile -Encoding ASCII -Value @"
[Unit]
Description=PolliPi Field Observer API
After=network.target

[Service]
User=$User
WorkingDirectory=$RemoteDir
ExecStart=/usr/bin/python3 -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 3
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"@
  Set-Content -LiteralPath $profileFile -Encoding ASCII -Value @"
[Service]
Environment=POLLIPI_DEVICE_ID=$resolvedDeviceId
Environment="POLLIPI_DEVICE_NAME=$($profile.DeviceName)"
Environment="POLLIPI_CAMERA_LABEL=$($profile.CameraLabel)"
Environment=POLLIPI_CAMERA_MODEL=$($profile.CameraModel)
Environment=POLLIPI_CAMERA_PROFILE=$($profile.CameraProfile)
Environment=POLLIPI_IS_AI_CAMERA=$($profile.IsAi)
Environment=POLLIPI_IS_NOIR=$($profile.IsNoir)
Environment=POLLIPI_IS_WIDE=$($profile.IsWide)
"@
  $env:SSH_ASKPASS = $askpass
  $env:SSH_ASKPASS_REQUIRE = "force"
  $env:DISPLAY = "pollipi"

  & ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no $target "mkdir -p '$RemoteDir'"
  if ($LASTEXITCODE -ne 0) { throw "remote directory creation failed with exit code $LASTEXITCODE" }

  & scp -r -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new @sourceFiles "${target}:${RemoteDir}/"
  if ($LASTEXITCODE -ne 0) { throw "scp failed with exit code $LASTEXITCODE" }
  & scp -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new $serviceFile "${target}:${RemoteDir}/pollipi.service"
  if ($LASTEXITCODE -ne 0) { throw "service scp failed with exit code $LASTEXITCODE" }
  & scp -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new $profileFile "${target}:${RemoteDir}/camera-profile.conf"
  if ($LASTEXITCODE -ne 0) { throw "profile scp failed with exit code $LASTEXITCODE" }

  $escapedPassword = $env:POLLIPI_DEPLOY_PASSWORD -replace "'", "'\''"
  $installCommand = ""
  if ($InstallDependencies) {
    $installCommand = "printf '%s\n' '$escapedPassword' | sudo -S -p '' apt-get update && printf '%s\n' '$escapedPassword' | sudo -S -p '' apt-get install -y python3-fastapi python3-uvicorn &&"
  }
  $remote = "$installCommand cd '$RemoteDir' && python3 -m py_compile pollipi_api_server.py imx500_detect_test.py && printf '%s\n' '$escapedPassword' | sudo -S -p '' mkdir -p /etc/systemd/system/pollipi.service.d && printf '%s\n' '$escapedPassword' | sudo -S -p '' cp '$RemoteDir/pollipi.service' /etc/systemd/system/pollipi.service && printf '%s\n' '$escapedPassword' | sudo -S -p '' cp '$RemoteDir/camera-profile.conf' /etc/systemd/system/pollipi.service.d/camera-profile.conf && printf '%s\n' '$escapedPassword' | sudo -S -p '' systemctl daemon-reload && printf '%s\n' '$escapedPassword' | sudo -S -p '' systemctl enable --now pollipi.service && printf '%s\n' '$escapedPassword' | sudo -S -p '' systemctl restart pollipi.service && sleep 2 && curl -sS http://127.0.0.1:8000/device"

  & ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no $target $remote
  if ($LASTEXITCODE -ne 0) { throw "remote setup failed with exit code $LASTEXITCODE" }
}
finally {
  if (Test-Path -LiteralPath $askpass) {
    Remove-Item -LiteralPath $askpass -Force
  }
  if (Test-Path -LiteralPath $serviceFile) {
    Remove-Item -LiteralPath $serviceFile -Force
  }
  if (Test-Path -LiteralPath $profileFile) {
    Remove-Item -LiteralPath $profileFile -Force
  }
  $env:SSH_ASKPASS = $oldAskpass
  $env:SSH_ASKPASS_REQUIRE = $oldAskpassRequire
  $env:DISPLAY = $oldDisplay
}
