# GL.iNet Field LAN Transfer

Use this when the GL-MT300N-V2 LAN has no internet, but the PC still needs
internet for Codex/GitHub.

## Recommended topology

Keep the PC on its normal internet Wi-Fi. Connect the PC to the GL router with an
Ethernet cable from the PC Ethernet port to a GL LAN port.

```text
internet Wi-Fi  -> PC -> Codex/GitHub stays online
PC Ethernet     -> GL LAN 192.168.8.1 -> Pi 192.168.8.11-15
iPad Wi-Fi      -> GL SSID
Pi Wi-Fi        -> GL SSID
```

If the PC has no Ethernet port, use a USB-Ethernet adapter. Do not switch the
PC's Wi-Fi to `GL-MT300N-V2-aa1` unless the GL router has WAN internet.

## Windows checks

After plugging Ethernet into the GL LAN port:

```powershell
ipconfig
Test-NetConnection 192.168.8.1 -Port 80
Test-NetConnection 192.168.8.11 -Port 22
```

Expected:

- Wi-Fi still has internet.
- Ethernet has an address like `192.168.8.x`.
- `192.168.8.1` reaches the GL router.
- each Pi answers on SSH port 22.

If Ethernet does not get DHCP, set a temporary static IPv4 address on the
Ethernet adapter:

```text
IP address: 192.168.8.200
Subnet:     255.255.255.0
Gateway:    leave blank, or 192.168.8.1
DNS:        leave blank
```

Leaving gateway/DNS blank helps Windows keep internet traffic on the existing
Wi-Fi while using Ethernet only for `192.168.8.0/24`.

## Build on the internet side

Run these before touching real Pi devices:

```powershell
pnpm build:web
$env:PYTHONPATH='packages/server/src;packages/analysis/src'
python -m visit_monitor_server.distribution.bundle_single_file --output dist/pollipi_api_server.py
python -m py_compile dist/pollipi_api_server.py
```

## Dry-run fleet deployment

Copy `tools/fleet.gl-lan.example.json` to a local ignored file and edit if needed:

```powershell
Copy-Item tools/fleet.gl-lan.example.json pollipi-transfer/fleet.local.json
python tools/pollipi_fleet_deploy.py --config pollipi-transfer/fleet.local.json
```

The default command is dry-run. It checks local artifacts and prints the SSH/SCP
plan without touching Pi files.

## Execute one controlled rollout

Only after dry-run and reachability checks pass:

```powershell
python tools/pollipi_fleet_deploy.py --config pollipi-transfer/fleet.local.json --execute --confirm-live-deploy
```

The deploy tool runs one Pi at a time, stops on failure, backs up the current
artifact/web build, restarts the service, then verifies `/device` build metadata.

## Other workable options

- Temporarily give the GL router WAN internet through a phone hotspot or another
  upstream network. Then PC can join the GL Wi-Fi without losing Codex.
- Use a USB-Ethernet adapter as the simplest field kit item.
- iPad-only field updates are possible only with a separate SSH/SFTP app and a
  prebuilt bundle already stored in Files. This is not the recommended normal
  deployment path.
