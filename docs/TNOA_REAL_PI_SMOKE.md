# TNOA real Raspberry Pi smoke gate

This gate verifies the Phase-A TNOA field bridge on an actual self-hosted Raspberry Pi without enabling calibrated field decisions or adaptive TNOA actions.

## What it tests

When `.github/workflows/server-ci.yml` is started manually with:

- `run_pi_smoke=true`
- `real_camera_smoke=true`

its `Pi Smoke Test (arm64)` job must run on a self-hosted runner labelled:

```text
self-hosted, linux, arm64, raspberry-pi
```

The job:

1. downloads the exact single-file server artifact produced by the Ubuntu build job;
2. refuses to stop an already-active `pollipi.service` automatically;
3. requires `picamera2` and at least one detected physical camera;
4. starts the bundled server locally with `POLLIPI_FAKE_CAMERA=0`;
5. keeps `POLLIPI_LIVE_ADAPTIVE_ENABLED=0`;
6. runs a short fixed-interval capture with one-second low-resolution probes;
7. stops capture cleanly;
8. requires exactly one `tnoa_observation_v1_<run_id>.csv` file with multiple probe rows;
9. verifies that every row remains fail-closed:
   - `calibration_status=unavailable`;
   - `observation_state=U`;
   - `would_be_action=observe_only`;
   - `action_applied=False`;
   - all calibrated T/N/O/C/A- support fields empty;
   - `coupled_available=False`;
   - `absence_available=False`;
10. verifies real frame availability and measured probe timing, plus the smoke-session join metadata.

The captured images, TNOA CSV and server log are uploaded as seven-day validation artifacts.

## Safety boundary

This is a hardware integration smoke, not field calibration.

Passing it does **not** establish:

- target recall or precision;
- nuisance false-attribution control in nature;
- calibrated observability;
- target-coupled response validity;
- biological absence certification;
- superiority of adaptive capture;
- a field visit-rate estimate.

The field calibration manifest remains unfrozen and cannot be loaded as a live policy.

## Why an active PolliPi service causes a fail

A camera can normally be owned by only one active capture process. The workflow deliberately refuses to issue `sudo systemctl stop pollipi.service` because an unattended field service may be collecting real data. If the smoke reports that `pollipi.service` is active, stop it intentionally on a designated test Pi and rerun the manual workflow.

## Fake-camera mode

`run_pi_smoke=true` with `real_camera_smoke=false` retains the self-hosted fake-camera smoke. That path checks ARM/server packaging but is not evidence that Camera Module capture works.

## Next scientific step after a real-camera PASS

Collect synchronized primary-Pi and independent reference-truth recordings. Produce blinded Phase-B annotation sheets and freeze the development/held-out split and numerical calibration rule before held-out scoring. Do not promote the smoke output itself into calibration data unless the recording was prospectively designated for development calibration.
