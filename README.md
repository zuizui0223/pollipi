# PolliPi Field Observer

PolliPi is a **local-first Raspberry Pi observation system** for flower visitors.

```text
scheduled still-image record
+ low-resolution probe analysis
+ whole-frame overlapping mesh decisions
+ per-probe provenance and shadow logging
+ optional live canary modes for denser stills or a short candidate video
```

It is **not** an automatic pollinator classifier, a pure motion-triggered camera, or a field-time ML training system. A mesh decision is always supporting metadata; it is never a confirmed visit.

> 日本語の実際の操作手順: [現行運用ガイド](docs/OPERATION_GUIDE_JA.md)

## System role and operating principle

- Each Pi runs capture autonomously after a session has been started.
- The iPad is a direct local control and inspection console.
- A coordinator / central server is **not required** for normal laboratory or field-LAN operation.
- The field router only needs to place the iPad and Pis on the same private Wi-Fi LAN. WAN, SIM, and cloud access are unnecessary.
- The scientific record and the mesh decision are deliberately separated: the image sequence remains available for later human review even when a candidate decision is wrong.

PolliPi has four user-facing capture modes. **①②③ record still images only** so they compare on the same output (how a fixed still budget is allocated in time); **④ adds video** as a separate hybrid. Their roles are intentionally different:

1. **① Plain timelapse is the primary field record.** It provides a fixed, comparable observation effort and always retains scheduled still images.
2. **② Motion-reactive is a basic responsive-recording mode.** It increases still-image density whenever anything moves, including wind, shadow, flower sway, camera movement, or an insect. Stills only.
3. **③ Classified adaptive filters environmental motion.** It attempts to reject broad environmental motion and keeps ambiguous local activity in denser stills. Stills only — no video. It remains a canary / validation mode until real field data establish its error rates.
4. **④ Classified + video is ③ plus a confirmation clip.** On a strong local candidate it records one short video, then a cooldown. The clip is a high-information confirmation aid, not a confirmed visit.

## Capture modes

| Mode | Current runtime behaviour | Intended role | Field status |
| --- | --- | --- | --- |
| **① Plain timelapse** | Fixed-interval scheduled still JPEGs. Low-resolution probes and three-stage decisions run in shadow mode only. | Standard scientific record and validation baseline. | **Default for routine field work.** |
| **② Motion-reactive** | Any state other than `no_activity` uses the fast still interval. Wind, shadow, shake, flower sway, and insects are intentionally treated alike. No video. | Basic safety-side mode for recording a moving period more densely. | Use only for a deliberate comparison session or designated Pi; it is not a visitor classifier. |
| **③ Classified adaptive** | `environmental_noise` stays at the normal interval; ambiguous or strong local activity uses the fast still interval. **Stills only — no video.** | Noise-filtered adaptive stills; the classification arm of the comparison without the video confounder. | **Canary / validation only** until tested against real flower, wind, illumination, and camera conditions. |
| **④ Classified + video** | Like ③, but two consecutive local candidates with at least one `strong_visitation_candidate` also trigger one short video clip, then cooldown. | Candidate-confirmation aid and high-information visit footage. | **Canary / validation only**; use when the question is candidate-clip quality, not the stills-cost comparison. |

### Live-adaptive safety gate

Modes ②, ③, and ④ alter real capture timing only when **all three** conditions are true:

1. The Pi service environment has `POLLIPI_LIVE_ADAPTIVE_ENABLED=1`.
2. The selected policy profile has `live_allowed=true`.
3. The `/start` request has `live_adaptive_requested=true`.

If any gate is off, the session falls back to fixed-interval capture with shadow logging. This makes live adaptation opt-in at the device, profile, and session levels.

The active profile mapping is:

- ① Plain → no live profile request; server defaults to `three_stage_default_v1` in shadow mode.
- ② Motion-reactive → `three_stage_motion_canary_v1`.
- ③ Classified adaptive (stills) → `three_stage_canary_v1`.
- ④ Classified + video → `three_stage_video_canary_v1`.

The user-selected fast interval must be shorter than the normal interval.

## What is recorded

### Primary still-image record

For ordinary field sessions, use **① Plain timelapse** with a fixed interval, normally **30 seconds**. This produces the comparable high-resolution still-image record used for manual visit labels and for evaluating modes ②, ③, and ④.

- ① saves fixed-interval still JPEGs.
- ② saves normal-interval or fast-interval still JPEGs according to whether there is any motion.
- ③ saves normal-interval or fast-interval still JPEGs according to the classified state; it does not record video.
- ④ uses a video-capable camera configuration. Its routine stills are captured from the 1080p main stream, and a HIGH trigger writes a short video clip instead of a still on that triggering probe.
- A candidate video is a confirmation aid, **not** a confirmed pollinator observation.

Do not compare image counts, video-trigger counts, or adaptive capture counts directly with visit frequency. Observation effort changes with mode and environmental movement.

### Low-resolution probes and evidence

The runtime normally analyses a low-resolution frame every **5 seconds** without saving every probe image.

On entry into one contiguous local-candidate episode (`uncertain_local_activity` or `strong_visitation_candidate`), PolliPi saves one small grayscale evidence pair:

- the immediately previous low-resolution probe frame;
- the current low-resolution probe frame.

These files are stored under `shadow_evidence/` and are a review aid only. They are not the primary scientific image record and are not saved for `no_activity` or `environmental_noise`.

### Mesh decision states

The active analysis evaluates whole-frame rectangular meshes plus a half-cell-offset mesh. It reports one of these states:

| State | Meaning | ① Plain effect | ② Motion-reactive effect | ③ Classified (stills) effect | ④ Classified + video effect |
| --- | --- | --- | --- | --- | --- |
| `no_activity` | Activity is below the quiet threshold. | Keep fixed interval. | Keep normal interval. | Keep normal interval. | Keep normal interval. |
| `environmental_noise` | Broad/global change, for example broad wind, shadow, illumination change, or camera shift. | Keep fixed interval. | Use fast interval: any motion counts. | Keep normal interval. | Keep normal interval. |
| `uncertain_local_activity` | Local but ambiguous motion. | Keep fixed interval; log would-be mode. | Use fast interval. | Use fast interval. | Use fast interval. |
| `strong_visitation_candidate` | Compact local motion that passes the current strong-candidate rule. | Keep fixed interval; log would-be mode. | Use fast interval. | Use fast interval (stills; no video). | Contributes to the two-probe condition for one short candidate video. |

The classifier uses small global-shift registration, brightness normalization, residual motion, overlapping mesh aggregation, and explainable rule thresholds. It is designed to avoid treating broad/global change as a visitor candidate, but **it does not assume the field is perfectly still**.

In particular, local flower movement can resemble local animal movement. Therefore:

- ① remains the reference record under all normal field conditions.
- ② deliberately treats local flower movement as a reason to record more densely.
- ③ and ④ must be evaluated separately for wind, flower sway, moving shadow, illumination change, and camera movement before the classifier is used as a scientific adaptive trigger.

## Recommended field use now

### Routine field sampling

Use **① Plain timelapse** on all Pis unless the session has a specific comparison purpose.

Recommended initial settings:

- normal interval: **30 seconds**;
- `Resume autonomously after Pi restart`: enabled when the session must survive a reboot;
- verify at least two successful saved stills on every Pi before leaving the system unattended;
- retain the shadow logs and candidate-evidence files for later validation.

### Comparing adaptive behaviour

Use ②, ③, or ④ only when the comparison is explicit in the field plan.

- Use **②** when the question is whether denser recording during any movement improves recoverable observations.
- Use **③** when the question is whether the classifier allocates a fixed still budget better than ① fixed and ② any-motion (stills-only, no video confounder).
- Use **④** when the question is whether the classifier can obtain useful candidate video clips without excessive false triggering.
- Record `camera_role`, `method_mode`, baseline interval, fast interval, policy profile, device ID, placement, and start time for every comparison session.
- Do not mix fixed and adaptive image counts as if they had equal observation effort.

## iPad quick operation

1. Connect the iPad and every Pi to the same private LAN.
2. Open one Pi in Safari at `http://<PI-IP>:8000/app/`.
3. Add the page to the home screen if desired.
4. Under **Add Raspberry Pi**, enter every other Pi IP address, for example `192.168.11.18`.
5. Confirm all device cards are online.
6. Choose **① Plain timelapse** and set `30 sec normal interval` for routine field work.
7. Enable **Resume autonomously after Pi restart** when reboot recovery is required.
8. Select **Start all**.
9. Confirm every card shows `capturing`, the intended `High-res interval`, and advancing `Last saved` / `Saved photos` values at least twice.
10. For ②, ③, or ④, confirm `live adaptive active` is actually on. If it is off, the system is intentionally running shadow-only fixed capture.

When a Pi is stopped, its card may show a low-resolution MJPEG framing preview. During capture, PolliPi releases the preview path to avoid camera contention and displays `Capturing` instead.

## Field router operation

A field router is used as a local Wi-Fi access point and DHCP server, not as an internet gateway.

- Set a fixed SSID and password.
- Keep DHCP enabled.
- Disable guest-network isolation / AP isolation / client isolation.
- Assign DHCP reservations for all five Pis.
- Prefer router-side DHCP reservations over Pi-side static IP configuration.
- On a separate field LAN such as `192.168.8.0/24`, reserve addresses like `.11` through `.15` for the Pis.

The detailed field readiness and disconnect/reboot tests are in [FIELD_READINESS_CHECKLIST.md](docs/FIELD_READINESS_CHECKLIST.md).

## Repository layout

```text
packages/
  analysis/     Pure shared mesh analysis + classifier (pipeline), policy/controller,
                simulation->runtime bridge, replay comparison, shadow runner
  server/       Raspberry Pi FastAPI runtime (the deployed device server)
  web/          iPad / browser field console (PWA)
  contracts/    Shared browser/API contracts
  coordinator/  Optional central coordinator server — NOT required for field-LAN use

dist/           Generated deployable server artifact (pollipi_api_server.py)
tools/          Fleet deploy utility (pollipi_fleet_deploy.py) + fleet configs + service template
docs/           Operation, deployment, validation, and field-readiness documents
```

The field runtime is exactly three packages: **`analysis` + `server` + `web`**. `coordinator`
is an optional multi-site control plane and plays no part in the direct iPad-to-Pi field-LAN
workflow. New development belongs in `packages/`; the deployment artifact is generated from
`packages/server` (with the embedded web build) into `dist/pollipi_api_server.py`.

## Build and deploy

### Build artifacts on Windows, macOS, Linux, or WSL

```bash
pnpm install
pnpm check:web
pnpm build:artifacts
```

`build:artifacts` intentionally builds the web app first and the server artifact second, so the packaged server embeds the same web build ID that will be deployed. The server build no longer relies on POSIX-only `PYTHONPATH=...` syntax.

### Full fleet deployment

Use `tools/pollipi_fleet_deploy.py` as the only deployment authority. Always dry-run first.

```powershell
python tools\pollipi_fleet_deploy.py --config tools\fleet.local.json
```

After reviewing the resolved hosts, artifact commit, web build ID, and rollback plan:

```powershell
python tools\pollipi_fleet_deploy.py `
  --config tools\fleet.local.json `
  --execute `
  --confirm-live-deploy
```

A full deployment backs up the current server and web build, uploads both artifacts, restarts the configured service, then verifies the deployed commit and web build ID. It stops at the first failed Pi and rolls back that Pi when a post-upload step fails.

For a web-only change, use the explicit web-only mode only when the server artifact is intentionally unchanged. See [DEPLOY_TO_PI.md](docs/DEPLOY_TO_PI.md).

## Active API

```text
/device
/status
/policy-profiles
/start
/stop
/latest
/preview
/mjpeg
/images
```

Retired active surfaces include `/events`, `/training/*`, and `/roi/*`.

## Field readiness before data collection

A Pi is not field-ready merely because its card is visible on the iPad. Each Pi must pass:

1. fixed-interval capture verification;
2. iPad disconnect verification;
3. field-router disconnect/reconnect verification;
4. Pi reboot plus autonomous-resume verification;
5. storage, clock, image, and probe-log verification.

For live mode ②, ③, or ④, add a device-level canary test before field deployment:

1. confirm the three live-adaptive gates intentionally enable the chosen mode;
2. confirm the expected normal and fast intervals are applied;
3. for ④, confirm a candidate clip finalizes correctly and that subsequent still capture resumes;
4. inspect storage growth, temperature, power stability, and false triggering under actual placement conditions.

See [FIELD_READINESS_CHECKLIST.md](docs/FIELD_READINESS_CHECKLIST.md) for the exact go/no-go checklist.

## Validation status

Implemented:

- pure non-ML mesh analysis;
- scheduled still capture with autonomous restart support;
- 5-second low-resolution probes and per-run v2 probe logs;
- candidate-entry low-resolution evidence pairs;
- versioned policy profiles and three-gate live-adaptive protection;
- ① fixed timelapse, ② any-motion responsive stills, ③ classified adaptive stills, and ④ classified candidate-video runtime paths;
- direct iPad-to-Pi local-LAN control;
- packaged artifact and safe fleet deployment flow.

Still required before **broad scientific use of ③ / ④ classified adaptive capture**:

- real fixed-interval Pi image sequences under each target flower and camera placement;
- manual comparison between visible insects, shadow decisions, and candidate clips;
- false-positive and missed-signal assessment by wind, flower sway, illumination, moving shadow, and camera stability;
- storage, power, temperature, and video-encoding endurance checks on actual Pi hardware;
- threshold calibration and a documented canary-to-field promotion criterion.

## Security and networking

Keep the Pi API on a private trusted LAN. Do not expose port 8000 directly to the public internet.

`POLLIPI_DEVICE_SECRET` is intended for a future coordinator-managed or remote-access deployment. It is not needed for the current direct iPad-to-Pi field LAN workflow. A shared secret is not a substitute for TLS, VPN, or a private network.
