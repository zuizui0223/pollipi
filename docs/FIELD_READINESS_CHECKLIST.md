# PolliPi field-readiness checklist

This checklist is for the current PolliPi architecture:

```text
scheduled high-resolution JPEG timelapse
+ low-resolution probe analysis
+ whole-frame overlapping mesh decisions
+ shadow-mode metadata logging
```

It is not a checklist for the retired ROI, event-review, or Pi-side ML workflow.

Read [OPERATION_GUIDE_JA.md](OPERATION_GUIDE_JA.md) before using this checklist for the first time.

## Before leaving for the field

### Build and fleet deployment

- [ ] Run `pnpm install` on the development machine.
- [ ] Run `pnpm check:web`.
- [ ] Run `pnpm build:artifacts` so the web build is created before the packaged server artifact.
- [ ] Use the fleet deployment configuration as the only source of truth for the five Pi hosts, SSH user, remote directories, systemd service name, and expected `/app/` URL.
- [ ] Run a dry-run deployment first.
- [ ] Confirm the dry-run contains only the intended Pi IP addresses.
- [ ] For a web-only update, do not replace the server artifact.
- [ ] For every Pi, verify after deployment:
  - [ ] `GET /device` returns 200.
  - [ ] `GET /status` returns 200.
  - [ ] `GET /policy-profiles` returns 200 and lists the expected profiles.
  - [ ] `GET /app/` returns 200.
  - [ ] At least one JavaScript/CSS asset referenced by `/app/` returns 200.
  - [ ] The packaged server commit and web build ID are the expected version.
- [ ] Confirm rollback is available for a failed individual Pi before continuing to the next Pi.

### Field router

- [ ] Use a dedicated private field SSID and password.
- [ ] Keep DHCP enabled on the router.
- [ ] Disable guest-network isolation, AP isolation, and client isolation.
- [ ] Create DHCP reservations for all five Pis; do not rely on Pi-side static IPs.
- [ ] Record the five reserved IPs in the field notebook and iPad device list.
- [ ] Confirm the iPad and every Pi are on the same router LAN.
- [ ] Confirm no field workflow depends on WAN, SIM, cloud services, or a coordinator.

### iPad console

- [ ] Open the console Pi at `http://<console-pi-ip>:8000/app/` in Safari.
- [ ] Confirm all five Pi cards are registered by direct IP address.
- [ ] Confirm the deployed commit / web build shown on every card is the expected version.
- [ ] Choose `three_stage_default_v1` for initial field sessions.
- [ ] Set the high-resolution baseline interval, normally 30 seconds.
- [ ] Enable **Resume autonomously after Pi restart** before Start if reboot recovery is required.
- [ ] Do not use a coordinator / central server for the normal field LAN workflow.

### Autonomous capture

For each Pi separately:

- [ ] Start a fixed-interval capture session from the iPad.
- [ ] Confirm `capturing` is shown.
- [ ] Confirm `High-res interval` is the intended interval.
- [ ] Confirm `Shadow only` is `on` and `live adaptive` is disabled.
- [ ] Confirm `last_capture_time` advances at the configured interval.
- [ ] Confirm `capture_count` increases.
- [ ] Confirm the newest scheduled image changes.
- [ ] Confirm the iPad gallery lists the scheduled images.
- [ ] Confirm storage free space is sufficient for the intended session.

### Disconnect and reboot tests

For each Pi separately:

- [ ] Disconnect the iPad; scheduled capture continues for at least five minutes.
- [ ] Reconnect the iPad and confirm `capture_count` and `last_capture_time` advanced during the disconnect.
- [ ] Disconnect or power-cycle the field router; scheduled capture continues for at least five minutes.
- [ ] Reconnect the router and confirm the Pi becomes visible again.
- [ ] Reboot the Pi while autonomous resume is enabled.
- [ ] Confirm the service starts automatically.
- [ ] Confirm a new scheduled image is written after reboot without opening the iPad app.
- [ ] Confirm the resumed interval, selected policy profile, and shadow-only mode remain correct.

### Mesh and shadow mode

- [ ] Use fixed capture intervals.
- [ ] Keep live adaptive interval control disabled.
- [ ] Enable shadow-mode logging only.
- [ ] Confirm each scheduled image has a corresponding shadow metadata row.
- [ ] Confirm the log includes mesh decision, reason, active-cell proportion, offset agreement, global synchrony, and hypothetical next interval.
- [ ] Treat `strong_visitation_candidate` as supporting metadata, not a confirmed visit.

### Network and data safety

- [ ] Keep Pi APIs on the private field LAN or a private overlay network.
- [ ] Do not expose Pi port 8000 directly to the public internet.
- [ ] Check clocks on every Pi before sampling.
- [ ] Record the router SSID, Pi IPs, policy profile, baseline interval, start time, and camera placement in the field notebook.
- [ ] Confirm the SD card image directory and shadow CSV are backed up after recovery.

## Field go/no-go rule

A Pi is ready only when it passes the autonomous-capture and reboot/disconnect tests above. A working iPad status card alone is not sufficient evidence that scheduled images are continuing to be saved.
