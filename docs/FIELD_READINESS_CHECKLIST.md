# PolliPi field-readiness checklist

This checklist is for the **current** PolliPi architecture:

```text
scheduled timelapse images
+ whole-frame overlapping mesh analysis
+ shadow-mode metadata logging
```

It is not a checklist for the retired ROI, event-review, or Pi-side ML workflow.

## Before leaving for the field

### Build and fleet deployment

- [ ] Build the packaged server artifact with `pnpm build:server`.
- [ ] Build the iPad web app with `pnpm check:web && pnpm build:web`.
- [ ] Use the fleet deployment configuration as the only source of truth for the five Pi hosts, SSH user, remote directories, systemd service name, and expected `/app/` URL.
- [ ] Run a dry-run deployment first.
- [ ] For a web-only update, do not replace the server artifact.
- [ ] For every Pi, verify after deployment:
  - [ ] `GET /device` returns 200.
  - [ ] `GET /status` returns 200.
  - [ ] `GET /app/` returns 200.
  - [ ] At least one JavaScript/CSS asset referenced by `/app/` returns 200.
  - [ ] The web build ID is the expected version when available.
- [ ] Confirm rollback is available for a failed individual Pi before continuing to the next Pi.

### Autonomous capture

For each Pi separately:

- [ ] Start a fixed-interval capture session from the iPad.
- [ ] Confirm `capturing` is shown.
- [ ] Confirm `last_capture_time` advances at the configured interval.
- [ ] Confirm `capture_count` increases.
- [ ] Confirm the newest scheduled image changes.
- [ ] Confirm the iPad gallery lists the scheduled images.
- [ ] Confirm storage free space is sufficient for the intended session.

### Disconnect and reboot tests

For each Pi separately:

- [ ] Disconnect the iPad; scheduled capture continues.
- [ ] Disconnect or reboot the field router; scheduled capture continues.
- [ ] Reconnect the router and confirm the Pi becomes visible again.
- [ ] Reboot the Pi and confirm the service starts automatically.
- [ ] Confirm a new scheduled image is written after reboot without opening the iPad app.

### Mesh and shadow mode

- [ ] Use fixed capture intervals.
- [ ] Keep live adaptive interval control disabled.
- [ ] Enable shadow-mode logging only.
- [ ] Confirm each scheduled image has a corresponding shadow metadata row.
- [ ] Confirm the log includes mesh decision, reason, active-cell proportion, offset agreement, global synchrony, and hypothetical next interval.
- [ ] Treat `strong_visitation_candidate` as supporting metadata, not a confirmed visit.

### Network and data safety

- [ ] Keep Pi APIs on the private field LAN or private overlay network.
- [ ] Do not expose Pi port 8000 directly to the public internet.
- [ ] When coordinator-managed access is used, set a distinct `POLLIPI_DEVICE_SECRET` per Pi and verify protected commands reject missing secrets.
- [ ] Verify that image deletion and export operations require the intended protection mode.
- [ ] Verify clocks are correct on every Pi before sampling.

## Field go/no-go rule

A Pi is ready only when it passes the autonomous-capture and reboot/disconnect tests above. A working iPad status card alone is not sufficient evidence that scheduled images are continuing to be saved.
